"""
Enhanced views for new AI chat features including voice, projects, and multimodal support
"""
import json
import uuid
import logging
from typing import Dict, Any
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import transaction

from .models import (
    ChatSession, ChatMessage, ChatProject, VoiceMessage, 
    MessageAttachment, UserMood, ConversationSummary, UserProfile
)
from .voice_utils import VoiceProcessor, get_audio_duration
from .multimodal_utils import ImageAnalyzer, MultimodalChatProcessor, detect_content_type
from .utils import ChatManager

logger = logging.getLogger('agent')


@method_decorator(csrf_exempt, name='dispatch')
class VoiceAPIView(View):
    """API endpoint for handling voice messages"""
    
    def post(self, request):
        """Handle voice message upload and processing"""
        
        try:
            session_id = request.POST.get('session_id')
            project_id = request.POST.get('project_id') or None
            audio_file = request.FILES.get('audio')
            
            if not session_id or not audio_file:
                return JsonResponse({
                    'success': False,
                    'error': 'Missing session_id or audio file'
                })
            
            # Get or create chat session
            session, created = ChatSession.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'user': request.user if request.user.is_authenticated else None
                }
            )
            
            # Set project if provided
            if project_id:
                try:
                    project = ChatProject.objects.get(id=project_id)
                    session.project = project
                    session.save()
                except ChatProject.DoesNotExist:
                    pass
            
            # Create chat message for voice
            chat_message = ChatMessage.objects.create(
                session=session,
                message_type='voice',
                content='[Голосовое сообщение]',  # Placeholder until transcribed
                timestamp=timezone.now()
            )
            
            # Calculate audio duration
            duration = get_audio_duration(audio_file)
            
            # Create voice message record
            voice_message = VoiceMessage.objects.create(
                chat_message=chat_message,
                audio_file=audio_file,
                duration=duration,
                status='uploading'
            )
            
            # Process voice message
            processor = VoiceProcessor()
            result = processor.process_voice_message(voice_message)
            
            if result.get('success'):
                # Generate AI response to transcribed text
                chat_manager = ChatManager()
                if voice_message.transcription:
                    ai_response = chat_manager.generate_response(
                        voice_message.transcription, 
                        session_id
                    )
                    
                    # Create AI response message
                    ChatMessage.objects.create(
                        session=session,
                        message_type='assistant',
                        content=ai_response,
                        timestamp=timezone.now()
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message_id': chat_message.id,
                        'transcription': voice_message.transcription,
                        'confidence': voice_message.confidence,
                        'ai_response': ai_response,
                        'duration': duration
                    })
                else:
                    return JsonResponse({
                        'success': True,
                        'message_id': chat_message.id,
                        'transcription': voice_message.transcription or '[Не удалось распознать]',
                        'confidence': voice_message.confidence,
                        'duration': duration
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Voice processing failed')
                })
                
        except Exception as e:
            logger.error(f"Voice API error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


@method_decorator(csrf_exempt, name='dispatch')
class MultimodalUploadView(View):
    """API endpoint for handling file uploads with multimodal processing"""
    
    def post(self, request):
        """Handle file upload and analysis"""
        
        try:
            session_id = request.POST.get('session_id')
            project_id = request.POST.get('project_id') or None
            uploaded_file = request.FILES.get('file')
            
            if not session_id or not uploaded_file:
                return JsonResponse({
                    'success': False,
                    'error': 'Missing session_id or file'
                })
            
            # Validate file size (10MB limit)
            max_size = 10 * 1024 * 1024
            if uploaded_file.size > max_size:
                return JsonResponse({
                    'success': False,
                    'error': 'File too large. Maximum size is 10MB.'
                })
            
            # Get or create chat session
            session, created = ChatSession.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'user': request.user if request.user.is_authenticated else None
                }
            )
            
            # Set project if provided
            if project_id:
                try:
                    project = ChatProject.objects.get(id=project_id)
                    session.project = project
                    session.save()
                except ChatProject.DoesNotExist:
                    pass
            
            # Detect content type
            file_content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset file pointer
            
            attachment_type = detect_content_type(file_content, uploaded_file.name)
            
            # Create chat message for file
            file_message = f"📎 Прикреплен файл: {uploaded_file.name}"
            chat_message = ChatMessage.objects.create(
                session=session,
                message_type='user',
                content=file_message,
                timestamp=timezone.now()
            )
            
            # Create attachment record
            attachment = MessageAttachment.objects.create(
                message=chat_message,
                file=uploaded_file,
                attachment_type=attachment_type,
                original_filename=uploaded_file.name,
                file_size=uploaded_file.size,
                mime_type=uploaded_file.content_type or 'application/octet-stream'
            )
            
            # Process file based on type
            analysis_result = {'success': True}
            
            if attachment_type == 'image':
                # Analyze image
                image_analyzer = ImageAnalyzer()
                analysis_result = image_analyzer.analyze_image(
                    uploaded_file, 
                    "Опиши что изображено на картинке и извлеки весь текст"
                )
                
                # Store analysis results
                attachment.analysis_result = analysis_result
                attachment.extracted_text = analysis_result.get('extracted_text', '')
                attachment.save()
                
                # Generate AI response about the image
                if analysis_result.get('success'):
                    image_context = f"Пользователь загрузил изображение '{uploaded_file.name}'. "
                    image_context += f"Описание: {analysis_result.get('description', '')}"
                    if analysis_result.get('extracted_text'):
                        image_context += f" Текст на изображении: {analysis_result.get('extracted_text')}"
                    
                    chat_manager = ChatManager()
                    ai_response = chat_manager.generate_response(image_context, session_id)
                    
                    ChatMessage.objects.create(
                        session=session,
                        message_type='assistant',
                        content=ai_response,
                        timestamp=timezone.now()
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message_id': chat_message.id,
                        'attachment_id': attachment.id,
                        'analysis': analysis_result.get('description', ''),
                        'extracted_text': analysis_result.get('extracted_text', ''),
                        'ai_response': ai_response
                    })
            
            # For other file types, provide basic response
            return JsonResponse({
                'success': True,
                'message_id': chat_message.id,
                'attachment_id': attachment.id,
                'analysis': f'Файл "{uploaded_file.name}" успешно загружен и сохранен.',
                'file_type': attachment_type
            })
            
        except Exception as e:
            logger.error(f"Multimodal upload error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


@method_decorator(csrf_exempt, name='dispatch')
class ProjectAPIView(View):
    """API endpoint for managing chat projects"""
    
    def get(self, request):
        """Get list of user's projects"""
        
        try:
            session_id = request.GET.get('session_id')
            
            # Get projects for authenticated user or session
            if request.user.is_authenticated:
                projects = ChatProject.objects.filter(
                    Q(user=request.user) | Q(is_shared=True)
                ).order_by('-updated_at')
            else:
                projects = ChatProject.objects.filter(
                    Q(session_id=session_id) | Q(is_shared=True)
                ).order_by('-updated_at')
            
            project_list = []
            for project in projects:
                project_list.append({
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'project_type': project.project_type,
                    'color': project.color,
                    'icon': project.icon,
                    'session_count': project.sessions.count(),
                    'created_at': project.created_at.isoformat(),
                    'updated_at': project.updated_at.isoformat()
                })
            
            return JsonResponse({
                'success': True,
                'projects': project_list
            })
            
        except Exception as e:
            logger.error(f"Project list error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def post(self, request):
        """Create new project"""
        
        try:
            data = json.loads(request.body)
            
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            project_type = data.get('project_type', 'general')
            color = data.get('color', '#0D1B2A')
            icon = data.get('icon', 'fas fa-folder')
            custom_prompt = data.get('custom_prompt', '').strip()
            
            if not name:
                return JsonResponse({
                    'success': False,
                    'error': 'Project name is required'
                })
            
            # Create new project
            project = ChatProject.objects.create(
                name=name,
                description=description,
                project_type=project_type,
                color=color,
                icon=icon,
                custom_prompt=custom_prompt,
                user=request.user if request.user.is_authenticated else None,
                session_id=data.get('session_id') if not request.user.is_authenticated else None
            )
            
            return JsonResponse({
                'success': True,
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'project_type': project.project_type,
                    'color': project.color,
                    'icon': project.icon
                }
            })
            
        except Exception as e:
            logger.error(f"Project creation error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


@method_decorator(csrf_exempt, name='dispatch')
class ChatHistorySearchView(View):
    """API endpoint for searching chat history"""
    
    def get(self, request):
        """Search through chat history"""
        
        try:
            session_id = request.GET.get('session_id')
            query = request.GET.get('query', '').strip()
            project_id = request.GET.get('project_id')
            
            if not session_id or not query:
                return JsonResponse({
                    'success': False,
                    'error': 'Missing session_id or query'
                })
            
            # Build search filters
            search_filters = Q(content__icontains=query)
            
            if project_id:
                search_filters &= Q(session__project_id=project_id)
            
            # Search in user's sessions
            if request.user.is_authenticated:
                search_filters &= Q(session__user=request.user)
            else:
                search_filters &= Q(session__session_id=session_id)
            
            # Execute search
            messages = ChatMessage.objects.filter(search_filters).select_related(
                'session', 'session__project'
            ).order_by('-timestamp')[:50]
            
            results = []
            for message in messages:
                results.append({
                    'id': message.id,
                    'content': message.content,
                    'message_type': message.message_type,
                    'timestamp': message.timestamp.isoformat(),
                    'session_id': message.session.session_id,
                    'project_name': message.session.project.name if message.session.project else None,
                    'session_title': message.session.get_title()
                })
            
            return JsonResponse({
                'success': True,
                'results': results,
                'total_found': len(results)
            })
            
        except Exception as e:
            logger.error(f"History search error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


@method_decorator(csrf_exempt, name='dispatch')
class MoodDetectionView(View):
    """API endpoint for mood detection and emotional intelligence"""
    
    def post(self, request):
        """Detect user mood from message"""
        
        try:
            data = json.loads(request.body)
            
            session_id = data.get('session_id')
            message_id = data.get('message_id')
            text = data.get('text', '').strip()
            
            if not session_id or not text:
                return JsonResponse({
                    'success': False,
                    'error': 'Missing session_id or text'
                })
            
            # Simple mood detection based on keywords
            mood = self._detect_mood_from_text(text)
            confidence = self._calculate_mood_confidence(text, mood)
            
            # Get session and message
            try:
                session = ChatSession.objects.get(session_id=session_id)
                message = ChatMessage.objects.get(id=message_id) if message_id else None
            except (ChatSession.DoesNotExist, ChatMessage.DoesNotExist):
                return JsonResponse({
                    'success': False,
                    'error': 'Session or message not found'
                })
            
            # Save mood detection
            user_mood = UserMood.objects.create(
                session=session,
                user=request.user if request.user.is_authenticated else None,
                mood=mood,
                confidence=confidence,
                message_trigger=message,
                detected_keywords=self._extract_mood_keywords(text)
            )
            
            return JsonResponse({
                'success': True,
                'mood': mood,
                'mood_display': dict(UserMood.MOOD_CHOICES)[mood],
                'confidence': confidence,
                'keywords': user_mood.detected_keywords
            })
            
        except Exception as e:
            logger.error(f"Mood detection error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def _detect_mood_from_text(self, text: str) -> str:
        """Simple keyword-based mood detection"""
        
        text_lower = text.lower()
        
        # Mood indicators
        happy_words = ['спасибо', 'отлично', 'супер', 'хорошо', 'класс', 'здорово', '😊', '😄', '👍']
        sad_words = ['грустно', 'печально', 'плохо', 'расстроен', '😢', '😞', '👎']
        angry_words = ['злой', 'бесит', 'раздражает', 'ненавижу', 'достало', '😠', '😡']
        excited_words = ['круто', 'восторг', 'потрясающе', 'фантастика', 'вау', '🤩', '🎉']
        confused_words = ['не понимаю', 'непонятно', 'сложно', 'запутался', '😕', '🤔']
        frustrated_words = ['не работает', 'ошибка', 'проблема', 'сложность', '😤', '😫']
        
        mood_scores = {
            'happy': sum(1 for word in happy_words if word in text_lower),
            'sad': sum(1 for word in sad_words if word in text_lower),
            'angry': sum(1 for word in angry_words if word in text_lower),
            'excited': sum(1 for word in excited_words if word in text_lower),
            'confused': sum(1 for word in confused_words if word in text_lower),
            'frustrated': sum(1 for word in frustrated_words if word in text_lower)
        }
        
        # Return mood with highest score, default to neutral
        if max(mood_scores.values()) > 0:
            return max(mood_scores, key=mood_scores.get)
        else:
            return 'neutral'
    
    def _calculate_mood_confidence(self, text: str, mood: str) -> float:
        """Calculate confidence score for mood detection"""
        
        text_lower = text.lower()
        total_words = len(text_lower.split())
        
        # Count mood-specific indicators
        mood_indicators = {
            'happy': ['спасибо', 'отлично', 'супер', 'хорошо'],
            'sad': ['грустно', 'печально', 'плохо'],
            'angry': ['злой', 'бесит', 'раздражает'],
            'excited': ['круто', 'восторг', 'потрясающе'],
            'confused': ['не понимаю', 'непонятно', 'сложно'],
            'frustrated': ['не работает', 'ошибка', 'проблема']
        }
        
        indicators = mood_indicators.get(mood, [])
        matches = sum(1 for word in indicators if word in text_lower)
        
        # Calculate confidence based on indicator density
        if total_words > 0:
            confidence = min(matches / total_words * 3, 1.0)  # Max confidence of 1.0
        else:
            confidence = 0.5  # Default confidence
        
        return round(confidence, 2)
    
    def _extract_mood_keywords(self, text: str) -> list:
        """Extract keywords that influenced mood detection"""
        
        text_lower = text.lower()
        all_mood_words = [
            'спасибо', 'отлично', 'супер', 'хорошо', 'грустно', 'плохо',
            'злой', 'бесит', 'круто', 'восторг', 'не понимаю', 'ошибка'
        ]
        
        found_keywords = [word for word in all_mood_words if word in text_lower]
        return found_keywords[:5]  # Return max 5 keywords


@method_decorator(csrf_exempt, name='dispatch')
class ConversationSummaryView(View):
    """API endpoint for generating conversation summaries"""
    
    def post(self, request):
        """Generate summary for a conversation"""
        
        try:
            data = json.loads(request.body)
            
            session_id = data.get('session_id')
            project_id = data.get('project_id')
            
            if not session_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Missing session_id'
                })
            
            # Get session
            try:
                session = ChatSession.objects.get(session_id=session_id)
            except ChatSession.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Session not found'
                })
            
            # Get messages for summary
            messages = session.messages.filter(
                message_type__in=['user', 'assistant']
            ).order_by('timestamp')
            
            if not messages.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'No messages to summarize'
                })
            
            # Generate summary
            summary_text = self._generate_summary(messages)
            key_topics = self._extract_key_topics(messages)
            action_items = self._extract_action_items(messages)
            
            # Create summary record
            summary = ConversationSummary.objects.create(
                session=session,
                project_id=project_id,
                summary=summary_text,
                key_topics=key_topics,
                action_items=action_items,
                message_count=messages.count(),
                date_range_start=messages.first().timestamp,
                date_range_end=messages.last().timestamp,
                confidence_score=0.8
            )
            
            return JsonResponse({
                'success': True,
                'summary': {
                    'id': summary.id,
                    'summary': summary_text,
                    'key_topics': key_topics,
                    'action_items': action_items,
                    'message_count': summary.message_count,
                    'date_range': {
                        'start': summary.date_range_start.isoformat(),
                        'end': summary.date_range_end.isoformat()
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def _generate_summary(self, messages) -> str:
        """Generate a summary of the conversation"""
        
        # Simple extractive summary for demo
        user_messages = [msg.content for msg in messages if msg.message_type == 'user']
        
        if not user_messages:
            return "Беседа без пользовательских сообщений"
        
        # Take first and last messages, plus any long ones
        summary_parts = []
        
        if len(user_messages) > 0:
            summary_parts.append(f"Пользователь начал с вопроса: {user_messages[0][:100]}...")
        
        if len(user_messages) > 2:
            summary_parts.append(f"В процессе обсуждались темы: {', '.join(user_messages[1:-1])[:200]}...")
        
        if len(user_messages) > 1:
            summary_parts.append(f"В конце пользователь спросил: {user_messages[-1][:100]}...")
        
        return " ".join(summary_parts)
    
    def _extract_key_topics(self, messages) -> list:
        """Extract key topics from conversation"""
        
        # Simple keyword extraction
        common_topics = [
            'расписание', 'экзамены', 'стипендия', 'документы', 
            'оценки', 'преподаватель', 'группа', 'семестр'
        ]
        
        all_text = " ".join([msg.content.lower() for msg in messages])
        found_topics = [topic for topic in common_topics if topic in all_text]
        
        return found_topics[:5]  # Return max 5 topics
    
    def _extract_action_items(self, messages) -> list:
        """Extract action items from conversation"""
        
        # Look for action-oriented phrases
        action_phrases = [
            'нужно', 'должен', 'необходимо', 'требуется', 
            'подать', 'оформить', 'получить', 'сдать'
        ]
        
        action_items = []
        for msg in messages:
            content_lower = msg.content.lower()
            for phrase in action_phrases:
                if phrase in content_lower:
                    # Extract sentence containing the action phrase
                    sentences = msg.content.split('.')
                    for sentence in sentences:
                        if phrase in sentence.lower():
                            action_items.append(sentence.strip())
                            break
        
        return action_items[:3]  # Return max 3 action items