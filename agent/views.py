import json
import uuid
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.db.models import Q
from .models import FAQEntry, ChatSession, ChatMessage, RequestLog
from .forms import ChatMessageForm, FAQSearchForm
from .utils import ChatManager, KnowledgeBaseManager
import logging

logger = logging.getLogger('agent')


class ChatView(View):
    """Main chat interface view"""
    
    def get(self, request):
        """Render the chat interface"""
        
        # Generate or get session ID
        session_id = request.session.get('chat_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            request.session['chat_session_id'] = session_id
            
            # Create new chat session
            ChatSession.objects.create(
                session_id=session_id,
                user=request.user if request.user.is_authenticated else None
            )
        
        # Get chat history
        chat_manager = ChatManager()
        chat_history = chat_manager.get_chat_history(session_id)
        
        # Initialize forms
        message_form = ChatMessageForm()
        search_form = FAQSearchForm()
        
        context = {
            'message_form': message_form,
            'search_form': search_form,
            'chat_history': chat_history,
            'session_id': session_id,
        }
        
        return render(request, 'chat.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class ChatAPIView(View):
    """API endpoint for handling chat messages"""
    
    def post(self, request):
        """Handle chat message submission"""
        
        try:
            # Parse JSON data
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            session_id = data.get('session_id', '')
            
            if not message:
                return JsonResponse({
                    'success': False,
                    'error': 'Message cannot be empty'
                }, status=400)
            
            if len(message) > 1000:
                return JsonResponse({
                    'success': False,
                    'error': 'Message too long (max 1000 characters)'
                }, status=400)
            
            # Get or create session
            session = None
            if session_id:
                try:
                    session = ChatSession.objects.get(session_id=session_id)
                except ChatSession.DoesNotExist:
                    session = ChatSession.objects.create(
                        session_id=session_id,
                        user=request.user if request.user.is_authenticated else None
                    )
            
            # Save user message
            if session:
                ChatMessage.objects.create(
                    session=session,
                    message_type='user',
                    content=message
                )
            
            # Process message with AI
            chat_manager = ChatManager()
            ai_response = chat_manager.process_message(message, session_id)
            
            # Save AI response
            if session and ai_response.get('success'):
                ChatMessage.objects.create(
                    session=session,
                    message_type='assistant',
                    content=ai_response.get('message', ''),
                    response_time=ai_response.get('response_time', 0),
                    tokens_used=ai_response.get('tokens_used', 0),
                    model_used=ai_response.get('model', '')
                )
            
            # Return response
            if ai_response.get('success'):
                return JsonResponse({
                    'success': True,
                    'message': ai_response.get('message', ''),
                    'response_time': ai_response.get('response_time', 0),
                    'session_id': session_id
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': ai_response.get('error', 'Unknown error occurred'),
                    'session_id': session_id
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Chat API error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Internal server error'
            }, status=500)


class FAQView(View):
    """FAQ search and display view with enhanced logging"""
    
    def get(self, request):
        """Handle FAQ search with automatic query logging"""
        
        form = FAQSearchForm(request.GET)
        entries = []
        
        if form.is_valid():
            query = form.cleaned_data.get('q', '')
            category = form.cleaned_data.get('category', '')
            
            if query or category:
                # Log the search query
                self.log_search_query(request, query)
                
                kb_manager = KnowledgeBaseManager()
                entries = kb_manager.search_faq(query, category, limit=20)
                
                # Update search query with results
                self.update_search_results(query, entries)
        
        return JsonResponse({
            'success': True,
            'entries': [
                {
                    'id': entry.id,
                    'question': entry.question,
                    'answer': entry.answer,
                    'category': entry.category,
                    'created_at': entry.created_at.isoformat()
                }
                for entry in entries
            ]
        })
    
    def log_search_query(self, request, query):
        """Log search query for knowledge base enhancement"""
        from .models import SearchQuery
        
        # Detect language
        language = 'ru'  # Default to Russian
        if any(char in query for char in 'abcdefghijklmnopqrstuvwxyz'):
            # Contains Latin characters, might be English
            english_words = ['schedule', 'document', 'exam', 'scholarship', 'admin']
            if any(word in query.lower() for word in english_words):
                language = 'en'
        
        # Get client info
        session_id = request.session.session_key
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check if similar query exists recently
        from django.utils import timezone
        from datetime import timedelta
        
        recent_threshold = timezone.now() - timedelta(hours=1)
        existing_query = SearchQuery.objects.filter(
            query=query,
            session_id=session_id,
            created_at__gte=recent_threshold
        ).first()
        
        if not existing_query:
            SearchQuery.objects.create(
                query=query,
                language=language,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
    
    def update_search_results(self, query, entries):
        """Update search query with results found"""
        from .models import SearchQuery
        
        # Find the most recent search query
        search_query = SearchQuery.objects.filter(query=query).order_by('-created_at').first()
        
        if search_query:
            search_query.results_found = len(entries) > 0
            search_query.save()
            
            # If no results found, mark for potential KB addition
            if not entries:
                search_query.should_add_to_kb = True
                search_query.save()


class ChatHistoryView(View):
    """API endpoint for retrieving chat history"""
    
    def get(self, request):
        """Get chat history for current session"""
        
        session_id = request.GET.get('session_id', '')
        
        if not session_id:
            return JsonResponse({
                'success': False,
                'error': 'Session ID required'
            }, status=400)
        
        try:
            session = ChatSession.objects.get(session_id=session_id)
            messages = session.messages.all()[:50]  # Limit to last 50 messages
            
            return JsonResponse({
                'success': True,
                'messages': [
                    {
                        'id': msg.id,
                        'type': msg.message_type,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat(),
                        'response_time': msg.response_time,
                        'tokens_used': msg.tokens_used
                    }
                    for msg in messages
                ]
            })
            
        except ChatSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Session not found'
            }, status=404)


class AnalyticsView(View):
    """Basic analytics view for admin users"""
    
    def get(self, request):
        """Get basic analytics data"""
        
        if not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized'
            }, status=403)
        
        # Get basic statistics
        total_messages = ChatMessage.objects.count()
        total_sessions = ChatSession.objects.count()
        total_requests = RequestLog.objects.count()
        successful_requests = RequestLog.objects.filter(api_success=True).count()
        
        # Recent activity
        recent_logs = RequestLog.objects.all()[:10]
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_messages': total_messages,
                'total_sessions': total_sessions,
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0
            },
            'recent_activity': [
                {
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'success': log.api_success,
                    'response_time': log.response_time,
                    'tokens_used': log.tokens_used
                }
                for log in recent_logs
            ]
        })


class SystemStatusView(View):
    """System status view for admin dashboard"""
    
    def get(self, request):
        """Get current system configuration status"""
        
        if not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized'
            }, status=403)
        
        from .models import AIModelConfig, SystemPrompt, APIKeyConfig
        
        # Get active configurations
        active_model = AIModelConfig.objects.filter(is_active=True).first()
        active_prompt = SystemPrompt.objects.filter(prompt_type='system', is_active=True).first()
        active_api = APIKeyConfig.objects.filter(is_active=True).first()
        
        # Get total counts
        total_models = AIModelConfig.objects.count()
        total_prompts = SystemPrompt.objects.count()
        total_apis = APIKeyConfig.objects.count()
        
        return JsonResponse({
            'success': True,
            'current_config': {
                'model': {
                    'name': active_model.name if active_model else 'None',
                    'model_name': active_model.model_name if active_model else 'None',
                    'max_tokens': active_model.max_tokens if active_model else 0,
                    'temperature': active_model.temperature if active_model else 0.0,
                    'is_active': bool(active_model)
                },
                'prompt': {
                    'name': active_prompt.name if active_prompt else 'None',
                    'type': active_prompt.prompt_type if active_prompt else 'None',
                    'is_active': bool(active_prompt)
                },
                'api': {
                    'provider': active_api.provider if active_api else 'None',
                    'url': active_api.api_url if active_api else 'None',
                    'is_active': bool(active_api)
                }
            },
            'counts': {
                'total_models': total_models,
                'total_prompts': total_prompts,
                'total_apis': total_apis,
                'total_faq_entries': FAQEntry.objects.filter(is_active=True).count()
            }
        })
