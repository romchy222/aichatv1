from django.urls import path
from . import views

app_name = 'agent'

urlpatterns = [
    # Main chat interface
    path('', views.ChatView.as_view(), name='chat'),
    
    # API endpoints
    path('api/chat/', views.ChatAPIView.as_view(), name='chat_api'),
    path('api/faq/', views.FAQView.as_view(), name='faq_api'),
    path('api/history/', views.ChatHistoryView.as_view(), name='history_api'),
    path('api/analytics/', views.AnalyticsView.as_view(), name='analytics_api'),
    path('api/system-status/', views.SystemStatusView.as_view(), name='system_status_api'),
]
