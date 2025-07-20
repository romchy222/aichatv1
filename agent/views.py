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
from .models import (
    FAQEntry, ChatSession, ChatMessage, RequestLog, FileUpload,
    UserProfile, Notification, UserNotification, EventSchedule, Analytics
)
from .forms import ChatMessageForm, FAQSearchForm
from .utils import ChatManager, KnowledgeBaseManager
from .file_processors import FileProcessorManager
from .analytics import AnalyticsManager, NotificationManager
import logging

logger = logging.getLogger('agent')


class ChatView(View):
    """Main chat interface view"""
    
    def get(self, request):
        """Render the chat interface"""
        
        # Check if enhanced version is requested
        enhanced = request.GET.get('enhanced', 'false').lower() == 'true'
        
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
        
        # Choose template based on version
        template = 'enhanced-chat.html' if enhanced else 'chat.html'
        return render(request, template, context)


class EnhancedChatView(View):
    """Enhanced chat interface view with all new features"""
    
    def get(self, request):
        """Render the enhanced chat interface"""
        
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
        
        return render(request, 'enhanced-chat.html', context)


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


class AdvancedAnalyticsView(View):
    """Advanced analytics dashboard for admins"""
    
    def get(self, request):
        """Get comprehensive analytics data"""
        if not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized'
            }, status=403)
        
        days = int(request.GET.get('days', 7))
        analytics_manager = AnalyticsManager()
        
        try:
            dashboard_data = analytics_manager.get_dashboard_data(days)
            user_insights = analytics_manager.get_user_insights(days)
            
            return JsonResponse({
                'success': True,
                'dashboard': dashboard_data,
                'user_insights': user_insights
            })
            
        except Exception as e:
            logger.error(f"Error generating analytics: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to generate analytics'
            }, status=500)


class NotificationAPIView(View):
    """API for managing notifications"""
    
    def get(self, request):
        """Get user notifications"""
        session_id = request.GET.get('session_id', '')
        unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
        
        if not session_id:
            return JsonResponse({
                'success': False,
                'error': 'Session ID required'
            }, status=400)
        
        try:
            # Get or create user profile
            user_profile, created = UserProfile.objects.get_or_create(
                session_id=session_id,
                defaults={'preferred_language': 'ru', 'role': 'guest'}
            )
            
            notification_manager = NotificationManager()
            notifications = notification_manager.get_user_notifications(
                user_profile, unread_only
            )
            
            return JsonResponse({
                'success': True,
                'notifications': [
                    {
                        'id': n.id,
                        'title': n.notification.title,
                        'message': n.notification.message,
                        'type': n.notification.notification_type,
                        'priority': n.notification.priority,
                        'is_read': n.is_read,
                        'delivered_at': n.delivered_at.isoformat(),
                        'read_at': n.read_at.isoformat() if n.read_at else None
                    }
                    for n in notifications[:20]  # Limit to 20 notifications
                ]
            })
            
        except Exception as e:
            logger.error(f"Error fetching notifications: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch notifications'
            }, status=500)
    
    @method_decorator(csrf_exempt, name='dispatch')
    def post(self, request):
        """Mark notification as read"""
        try:
            data = json.loads(request.body)
            notification_id = data.get('notification_id')
            session_id = data.get('session_id', '')
            
            if not notification_id or not session_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Notification ID and session ID required'
                }, status=400)
            
            user_profile = UserProfile.objects.get(session_id=session_id)
            user_notification = UserNotification.objects.get(
                id=notification_id,
                user_profile=user_profile
            )
            
            user_notification.mark_as_read()
            
            return JsonResponse({'success': True})
            
        except (UserProfile.DoesNotExist, UserNotification.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Notification not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to update notification'
            }, status=500)


class EventScheduleAPIView(View):
    """API for event schedule"""
    
    def get(self, request):
        """Get upcoming events"""
        days_ahead = int(request.GET.get('days', 30))
        session_id = request.GET.get('session_id', '')
        
        try:
            # Get user profile to filter events by role/faculty
            user_profile = None
            if session_id:
                user_profile = UserProfile.objects.filter(session_id=session_id).first()
            
            # Get upcoming events
            from django.utils import timezone
            from datetime import timedelta
            
            end_date = timezone.now() + timedelta(days=days_ahead)
            
            events = EventSchedule.objects.filter(
                start_datetime__gte=timezone.now(),
                start_datetime__lte=end_date,
                is_active=True,
                is_cancelled=False
            )
            
            # Filter by user profile if available
            if user_profile and user_profile.role != 'guest':
                # Filter by faculty if user has one
                if user_profile.faculty:
                    events = events.filter(
                        Q(is_public=True) |
                        Q(target_faculties__contains=[user_profile.faculty])
                    )
                
                # Filter by course year if user has one
                if user_profile.course_year:
                    events = events.filter(
                        Q(is_public=True) |
                        Q(target_courses__contains=[user_profile.course_year])
                    )
            else:
                # Show only public events for guests
                events = events.filter(is_public=True)
            
            events = events.order_by('start_datetime')[:50]  # Limit to 50 events
            
            return JsonResponse({
                'success': True,
                'events': [
                    {
                        'id': event.id,
                        'title': event.title,
                        'description': event.description,
                        'event_type': event.event_type,
                        'start_datetime': event.start_datetime.isoformat(),
                        'end_datetime': event.end_datetime.isoformat() if event.end_datetime else None,
                        'is_all_day': event.is_all_day,
                        'location': event.location,
                        'room_number': event.room_number,
                        'is_upcoming': event.is_upcoming()
                    }
                    for event in events
                ]
            })
            
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch events'
            }, status=500)


class UserProfileAPIView(View):
    """API for user profile management"""
    
    def get(self, request):
        """Get user profile"""
        session_id = request.GET.get('session_id', '')
        
        if not session_id:
            return JsonResponse({
                'success': False,
                'error': 'Session ID required'
            }, status=400)
        
        try:
            user_profile, created = UserProfile.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'preferred_language': 'ru',
                    'role': 'guest'
                }
            )
            
            return JsonResponse({
                'success': True,
                'profile': {
                    'id': user_profile.id,
                    'preferred_language': user_profile.preferred_language,
                    'role': user_profile.role,
                    'faculty': user_profile.faculty,
                    'specialization': user_profile.specialization,
                    'course_year': user_profile.course_year,
                    'group_number': user_profile.group_number,
                    'email_notifications': user_profile.email_notifications,
                    'deadline_reminders': user_profile.deadline_reminders,
                    'system_announcements': user_profile.system_announcements,
                    'total_messages': user_profile.total_messages,
                    'last_active': user_profile.last_active.isoformat(),
                    'created_at': user_profile.created_at.isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching user profile: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch profile'
            }, status=500)
    
    @method_decorator(csrf_exempt, name='dispatch')
    def post(self, request):
        """Update user profile"""
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id', '')
            
            if not session_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Session ID required'
                }, status=400)
            
            user_profile, created = UserProfile.objects.get_or_create(
                session_id=session_id,
                defaults={'preferred_language': 'ru', 'role': 'guest'}
            )
            
            # Update fields if provided
            updatable_fields = [
                'preferred_language', 'role', 'faculty', 'specialization',
                'course_year', 'group_number', 'email_notifications',
                'deadline_reminders', 'system_announcements'
            ]
            
            updated_fields = []
            for field in updatable_fields:
                if field in data:
                    setattr(user_profile, field, data[field])
                    updated_fields.append(field)
            
            user_profile.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Profile updated: {", ".join(updated_fields)}',
                'updated_fields': updated_fields
            })
            
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to update profile'
            }, status=500)


class MetricsCollectionView(View):
    """Background endpoint for collecting metrics"""
    
    @method_decorator(csrf_exempt, name='dispatch')
    def post(self, request):
        """Collect metrics (to be called by cron job or scheduler)"""
        try:
            analytics_manager = AnalyticsManager()
            notification_manager = NotificationManager()
            
            # Collect daily metrics
            daily_metrics = analytics_manager.collect_daily_metrics()
            
            # Collect hourly metrics
            hourly_metrics = analytics_manager.collect_hourly_metrics()
            
            # Process notifications
            notifications_sent = notification_manager.process_scheduled_notifications()
            reminders_sent = notification_manager.process_event_reminders()
            
            return JsonResponse({
                'success': True,
                'daily_metrics': daily_metrics,
                'hourly_metrics': hourly_metrics,
                'notifications_sent': notifications_sent,
                'reminders_sent': reminders_sent
            })
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to collect metrics'
            }, status=500)
