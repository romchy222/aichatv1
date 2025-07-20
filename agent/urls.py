from django.urls import path
from . import views, enhanced_views

app_name = 'agent'

urlpatterns = [
    # Main chat interface
    path('', views.ChatView.as_view(), name='chat'),
    
    # Core API endpoints
    path('api/chat/', views.ChatAPIView.as_view(), name='chat_api'),
    path('api/faq/', views.FAQView.as_view(), name='faq_api'),
    path('api/history/', views.ChatHistoryView.as_view(), name='history_api'),
    path('api/analytics/', views.AnalyticsView.as_view(), name='analytics_api'),
    path('api/system-status/', views.SystemStatusView.as_view(), name='system_status_api'),
    
    # File handling endpoints
    path('api/files/', views.FileUploadView.as_view(), name='file_upload_api'),
    path('api/files/<int:file_id>/', views.FileContentView.as_view(), name='file_content_api'),
    
    # Enhanced features API endpoints
    path('api/voice/', enhanced_views.VoiceAPIView.as_view(), name='voice_api'),
    path('api/upload/', enhanced_views.MultimodalUploadView.as_view(), name='multimodal_upload_api'),
    path('api/projects/', enhanced_views.ProjectAPIView.as_view(), name='projects_api'),
    path('api/search/', enhanced_views.ChatHistorySearchView.as_view(), name='search_api'),
    path('api/mood/', enhanced_views.MoodDetectionView.as_view(), name='mood_api'),
    path('api/summary/', enhanced_views.ConversationSummaryView.as_view(), name='summary_api'),
]
