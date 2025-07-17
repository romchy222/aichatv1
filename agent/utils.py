import requests
import json
import time
import logging
from django.conf import settings
from .models import FAQEntry, RequestLog, ChatSession, AIModelConfig, SystemPrompt, APIKeyConfig, KnowledgeBaseEntry, SearchQuery
from django.db.models import Q

logger = logging.getLogger('agent')


class TogetherAIClient:
    """Client for interacting with Together.ai API"""
    
    def __init__(self):
        # Get active API configuration
        try:
            api_config = APIKeyConfig.objects.filter(provider='together', is_active=True).first()
            if api_config:
                self.api_key = api_config.api_key
                self.api_url = api_config.api_url
            else:
                self.api_key = settings.TOGETHER_API_KEY
                self.api_url = settings.TOGETHER_API_URL
        except:
            self.api_key = settings.TOGETHER_API_KEY
            self.api_url = settings.TOGETHER_API_URL
        
        # Get active model configuration
        try:
            model_config = AIModelConfig.objects.filter(is_active=True).first()
            if model_config:
                self.model = model_config.model_name
                self.max_tokens = model_config.max_tokens
                self.temperature = model_config.temperature
                self.top_p = model_config.top_p
                self.repetition_penalty = model_config.repetition_penalty
            else:
                self.model = "mistralai/Mistral-7B-Instruct-v0.1"
                self.max_tokens = 500
                self.temperature = 0.7
                self.top_p = 0.9
                self.repetition_penalty = 1.0
        except:
            self.model = "mistralai/Mistral-7B-Instruct-v0.1"
            self.max_tokens = 500
            self.temperature = 0.7
            self.top_p = 0.9
            self.repetition_penalty = 1.0
        
    def generate_response(self, messages, max_tokens=None, temperature=None):
        """Generate AI response using Together.ai API"""
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': max_tokens or self.max_tokens,
            'temperature': temperature or self.temperature,
            'top_p': self.top_p,
            'repetition_penalty': self.repetition_penalty,
            'stream': False
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                ai_message = data['choices'][0]['message']['content']
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                
                logger.info(f"AI response generated successfully in {response_time:.2f}s")
                
                return {
                    'success': True,
                    'message': ai_message,
                    'response_time': response_time,
                    'tokens_used': tokens_used,
                    'model': self.model
                }
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'response_time': response_time
                }
                
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'response_time': response_time
            }


class KnowledgeBaseManager:
    """Manager for handling knowledge base operations"""
    
    @staticmethod
    def search_faq(query, category=None, limit=5):
        """Search FAQ entries based on query and category"""
        
        if not query.strip():
            return []
        
        # Build search query
        search_filter = Q(is_active=True)
        
        if category:
            search_filter &= Q(category=category)
        
        # Search in question, answer, and keywords
        query_filter = (
            Q(question__icontains=query) |
            Q(answer__icontains=query) |
            Q(keywords__icontains=query)
        )
        
        search_filter &= query_filter
        
        # Search both FAQEntry and KnowledgeBaseEntry models
        faq_entries = list(FAQEntry.objects.filter(search_filter)[:limit//2])
        
        # Search in knowledge base entries
        kb_search_filter = Q(is_active=True)
        if category:
            kb_search_filter &= Q(category=category)
        
        kb_query_filter = (
            Q(question__icontains=query) |
            Q(answer__icontains=query) |
            Q(keywords__icontains=query)
        )
        
        kb_search_filter &= kb_query_filter
        
        kb_entries = list(KnowledgeBaseEntry.objects.filter(kb_search_filter)[:limit//2])
        
        # Combine results
        all_entries = faq_entries + kb_entries
        
        logger.info(f"Found {len(faq_entries)} FAQ entries and {len(kb_entries)} KB entries for query: {query}")
        
        return all_entries[:limit]
    
    @staticmethod
    def get_context_for_ai(user_message, max_entries=3):
        """Get relevant context from knowledge base for AI response"""
        
        # Extract keywords from user message
        keywords = user_message.lower().split()
        
        relevant_entries = []
        
        # Search for relevant FAQ entries
        for keyword in keywords:
            if len(keyword) > 2:  # Skip very short words
                entries = KnowledgeBaseManager.search_faq(keyword, limit=2)
                relevant_entries.extend(entries)
        
        # Remove duplicates and limit results
        seen_ids = set()
        unique_entries = []
        
        for entry in relevant_entries:
            if entry.id not in seen_ids:
                seen_ids.add(entry.id)
                unique_entries.append(entry)
                
                if len(unique_entries) >= max_entries:
                    break
        
        return unique_entries


class ChatManager:
    """Manager for handling chat operations"""
    
    def __init__(self):
        self.ai_client = TogetherAIClient()
        self.kb_manager = KnowledgeBaseManager()
    
    def process_message(self, user_message, session_id=None):
        """Process user message and generate AI response"""
        
        # Get or create chat session
        session = None
        if session_id:
            try:
                session = ChatSession.objects.get(session_id=session_id)
            except ChatSession.DoesNotExist:
                pass
        
        # Get relevant context from knowledge base
        kb_entries = self.kb_manager.get_context_for_ai(user_message)
        
        # Log search query if no KB entries found
        if not kb_entries:
            self.log_search_query_for_kb(user_message, session_id)
        
        # Build context string
        context = ""
        if kb_entries:
            context = "Relevant information from knowledge base:\n"
            for entry in kb_entries:
                context += f"Q: {entry.question}\nA: {entry.answer}\n\n"
        
        # Get active system prompt
        try:
            system_prompt = SystemPrompt.objects.filter(prompt_type='system', is_active=True).first()
            system_content = system_prompt.content if system_prompt else """Вы - полезный AI помощник для университета или образовательного учреждения. 
            Используйте предоставленную базу знаний для ответов на вопросы о расписании, документах, 
            стипендиях, экзаменах и администрации. 

            ВАЖНО: Всегда отвечайте на РУССКОМ языке, даже если вопрос задан на английском. 
            Поддерживайте также казахский язык при необходимости.
            
            Если не найдете соответствующую информацию в базе знаний, предоставьте общие 
            полезные советы и предложите обратиться в соответствующий отдел."""
        except:
            system_content = """Вы - полезный AI помощник для университета или образовательного учреждения. 
            Используйте предоставленную базу знаний для ответов на вопросы о расписании, документах, 
            стипендиях, экзаменах и администрации. 

            ВАЖНО: Всегда отвечайте на РУССКОМ языке, даже если вопрос задан на английском. 
            Поддерживайте также казахский язык при необходимости.
            
            Если не найдете соответствующую информацию в базе знаний, предоставьте общие 
            полезные советы и предложите обратиться в соответствующий отдел."""
        
        # Build messages for AI
        system_message = {
            "role": "system",
            "content": system_content
        }
        
        if context:
            context_message = {
                "role": "system",
                "content": context
            }
            messages = [system_message, context_message]
        else:
            messages = [system_message]
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Generate AI response
        ai_response = self.ai_client.generate_response(messages)
        
        # Log the request
        log_entry = RequestLog.objects.create(
            session=session,
            user_message=user_message,
            ai_response=ai_response.get('message', ''),
            response_time=ai_response.get('response_time', 0),
            api_success=ai_response.get('success', False),
            error_message=ai_response.get('error', ''),
            tokens_used=ai_response.get('tokens_used', 0)
        )
        
        # Associate KB entries with the log
        if kb_entries:
            # Separate FAQ entries from KB entries
            faq_entries = [entry for entry in kb_entries if hasattr(entry, '_meta') and entry._meta.model.__name__ == 'FAQEntry']
            kb_entries_new = [entry for entry in kb_entries if hasattr(entry, '_meta') and entry._meta.model.__name__ == 'KnowledgeBaseEntry']
            
            if faq_entries:
                log_entry.kb_entries_used.set(faq_entries)
            if kb_entries_new:
                log_entry.kb_entries_used_new.set(kb_entries_new)
        
        # Auto-generate KB entry if no existing KB entries and response is good
        if not kb_entries and ai_response.get('success'):
            self.generate_kb_entry_from_response(user_message, ai_response, session_id)
        
        return ai_response
    
    def log_search_query_for_kb(self, user_message, session_id=None):
        """Log search query for knowledge base enhancement when no KB entries found"""
        
        # Detect language
        language = 'ru'  # Default to Russian
        if any(char in user_message for char in 'abcdefghijklmnopqrstuvwxyz'):
            english_words = ['schedule', 'document', 'exam', 'scholarship', 'admin']
            if any(word in user_message.lower() for word in english_words):
                language = 'en'
        
        # Check if similar query exists recently
        from django.utils import timezone
        from datetime import timedelta
        
        recent_threshold = timezone.now() - timedelta(hours=1)
        existing_query = SearchQuery.objects.filter(
            query=user_message,
            session_id=session_id,
            created_at__gte=recent_threshold
        ).first()
        
        if not existing_query:
            SearchQuery.objects.create(
                query=user_message,
                language=language,
                results_found=False,
                should_add_to_kb=True,
                session_id=session_id
            )
    
    def generate_kb_entry_from_response(self, user_message, ai_response, session_id=None):
        """Generate knowledge base entry from AI response"""
        
        # Only generate if response is successful and substantial
        if not ai_response.get('success') or len(ai_response.get('message', '')) < 50:
            return None
        
        # Detect language
        language = 'ru'  # Default to Russian
        if any(char in user_message for char in 'abcdefghijklmnopqrstuvwxyz'):
            english_words = ['schedule', 'document', 'exam', 'scholarship', 'admin']
            if any(word in user_message.lower() for word in english_words):
                language = 'en'
        
        # Determine category based on keywords
        category = 'general'
        category_keywords = {
            'schedules': ['расписание', 'schedule', 'занятие', 'lesson', 'пара'],
            'documents': ['документ', 'document', 'справка', 'certificate', 'заявление'],
            'scholarships': ['стипендия', 'scholarship', 'выплата', 'payment'],
            'exams': ['экзамен', 'exam', 'зачет', 'test', 'сессия'],
            'administration': ['администрация', 'admin', 'деканат', 'office'],
            'dormitory': ['общежитие', 'dormitory', 'общага', 'hostel'],
            'library': ['библиотека', 'library', 'книга', 'book'],
            'fees': ['оплата', 'fee', 'плата', 'payment', 'стоимость']
        }
        
        for cat, keywords in category_keywords.items():
            if any(keyword in user_message.lower() for keyword in keywords):
                category = cat
                break
        
        # Create knowledge base entry
        kb_entry = KnowledgeBaseEntry.objects.create(
            question=user_message,
            answer=ai_response.get('message', ''),
            category=category,
            keywords=user_message.lower(),
            source='ai_generated',
            language=language,
            confidence_score=0.8,
            is_verified=False
        )
        
        # Update search query as added to KB
        search_query = SearchQuery.objects.filter(
            query=user_message,
            session_id=session_id
        ).order_by('-created_at').first()
        
        if search_query:
            search_query.ai_response = ai_response.get('message', '')
            search_query.added_to_kb = True
            search_query.save()
        
        return kb_entry
    
    def get_chat_history(self, session_id, limit=10):
        """Get chat history for a session"""
        
        try:
            session = ChatSession.objects.get(session_id=session_id)
            messages = session.messages.all()[:limit]
            return list(messages)
        except ChatSession.DoesNotExist:
            return []
