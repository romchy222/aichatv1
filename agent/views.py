import json
import uuid
import os
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
from .models import FAQEntry, ChatSession, ChatMessage, RequestLog, FileUpload
from .forms import ChatMessageForm, FAQSearchForm
from .utils import ChatManager, KnowledgeBaseManager
from .file_processors import FileProcessorManager
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
            ip_address = request.META.get('REMOTE_ADDR')
            ai_response = chat_manager.process_message(message, session_id, ip_address)
            
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
                raw_entries = kb_manager.search_faq(query, category, limit=20)
                
                # Apply content moderation to FAQ results
                from .utils import ContentModerator
                moderator = ContentModerator()
                session_id = request.session.session_key
                ip_address = request.META.get('REMOTE_ADDR')
                
                filtered_entries = []
                for entry in raw_entries:
                    # Filter question
                    question_mod = moderator.filter_content(
                        content=entry.question,
                        content_type='faq_result',
                        session_id=session_id,
                        ip_address=ip_address
                    )
                    
                    # Filter answer
                    answer_mod = moderator.filter_content(
                        content=entry.answer,
                        content_type='faq_result',
                        session_id=session_id,
                        ip_address=ip_address
                    )
                    
                    # Skip entries that are blocked
                    if question_mod['action'] == 'blocked' or answer_mod['action'] == 'blocked':
                        continue
                    
                    filtered_entries.append({
                        'id': entry.id,
                        'question': question_mod['filtered_content'],
                        'answer': answer_mod['filtered_content'],
                        'category': entry.category,
                        'created_at': entry.created_at.isoformat(),
                        'moderated': question_mod['is_filtered'] or answer_mod['is_filtered']
                    })
                
                # Update search query with results
                self.update_search_results(query, raw_entries)
        
        return JsonResponse({
            'success': True,
            'entries': filtered_entries
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


@method_decorator(csrf_exempt, name='dispatch')
class FileUploadView(View):
    """API endpoint for file uploads and processing"""
    
    def post(self, request):
        """Handle file upload"""
        try:
            if 'file' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'No file provided'
                }, status=400)
            
            uploaded_file = request.FILES['file']
            session_id = request.POST.get('session_id', '')
            
            # File size limit (10MB)
            if uploaded_file.size > 10 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'error': 'File size exceeds 10MB limit'
                }, status=400)
            
            # Determine file type
            file_manager = FileProcessorManager()
            file_type = file_manager.get_file_type(uploaded_file.name)
            
            # Save file
            file_content = ContentFile(uploaded_file.read())
            filename = default_storage.save(f'uploads/{uploaded_file.name}', file_content)
            file_path = default_storage.path(filename)
            
            # Get MIME type
            mime_type = file_manager.get_mime_type(file_path)
            
            # Create FileUpload record
            file_upload = FileUpload.objects.create(
                file=filename,
                original_filename=uploaded_file.name,
                file_type=file_type,
                file_size=uploaded_file.size,
                mime_type=mime_type,
                session_id=session_id,
                user=request.user if request.user.is_authenticated else None,
                status='processing'
            )
            
            # Process file
            try:
                result = file_manager.process_file(file_path, file_type)
                
                if result['success']:
                    file_upload.extracted_text = result['extracted_text']
                    file_upload.analysis_result = result['analysis']
                    file_upload.status = 'completed'
                else:
                    file_upload.status = 'failed'
                    
                file_upload.processed_at = timezone.now()
                file_upload.save()
                
                return JsonResponse({
                    'success': True,
                    'file_id': file_upload.id,
                    'filename': file_upload.original_filename,
                    'file_type': file_upload.get_file_type_display(),
                    'summary': result.get('summary', 'Файл обработан'),
                    'extracted_text': result.get('extracted_text', ''),
                    'processing_result': result
                })
                
            except Exception as e:
                logger.error(f"Error processing file {uploaded_file.name}: {e}")
                file_upload.status = 'failed'
                file_upload.save()
                
                return JsonResponse({
                    'success': False,
                    'error': f'Error processing file: {str(e)}'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }, status=500)
    
    def get(self, request):
        """Get list of uploaded files for session"""
        session_id = request.GET.get('session_id', '')
        
        if not session_id:
            return JsonResponse({
                'success': False,
                'error': 'Session ID required'
            }, status=400)
        
        files = FileUpload.objects.filter(session_id=session_id).order_by('-uploaded_at')[:20]
        
        return JsonResponse({
            'success': True,
            'files': [
                {
                    'id': f.id,
                    'filename': f.original_filename,
                    'file_type': f.get_file_type_display(),
                    'status': f.get_status_display(),
                    'uploaded_at': f.uploaded_at.isoformat(),
                    'file_size': f.file_size,
                    'has_text': bool(f.extracted_text)
                }
                for f in files
            ]
        })


class FileContentView(View):
    """API endpoint for retrieving file content"""
    
    def get(self, request, file_id):
        """Get extracted content from uploaded file"""
        try:
            file_upload = FileUpload.objects.get(id=file_id)
            
            return JsonResponse({
                'success': True,
                'file_info': {
                    'id': file_upload.id,
                    'filename': file_upload.original_filename,
                    'file_type': file_upload.get_file_type_display(),
                    'status': file_upload.get_status_display(),
                    'uploaded_at': file_upload.uploaded_at.isoformat(),
                    'processed_at': file_upload.processed_at.isoformat() if file_upload.processed_at else None,
                    'file_size': file_upload.file_size,
                },
                'extracted_text': file_upload.extracted_text,
                'analysis_result': file_upload.analysis_result
            })
            
        except FileUpload.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'File not found'
            }, status=404)


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
