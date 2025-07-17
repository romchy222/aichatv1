from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class FAQEntry(models.Model):
    """Model for storing FAQ entries in the knowledge base"""
    
    CATEGORY_CHOICES = [
        ('schedules', 'Schedules'),
        ('documents', 'Documents'),
        ('scholarships', 'Scholarships'),
        ('exams', 'Exams'),
        ('administration', 'Administration'),
        ('general', 'General'),
    ]
    
    question = models.TextField(help_text="FAQ question")
    answer = models.TextField(help_text="FAQ answer")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    keywords = models.TextField(help_text="Comma-separated keywords for search", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "FAQ Entry"
        verbose_name_plural = "FAQ Entries"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.category}: {self.question[:50]}..."


class ChatSession(models.Model):
    """Model for storing chat sessions"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"Session {self.session_id} - {self.created_at}"


class ChatMessage(models.Model):
    """Model for storing individual chat messages"""
    
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional fields for tracking AI response metadata
    response_time = models.FloatField(null=True, blank=True, help_text="Response time in seconds")
    tokens_used = models.IntegerField(null=True, blank=True)
    model_used = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."


class RequestLog(models.Model):
    """Model for logging API requests for analytics"""
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, null=True, blank=True)
    user_message = models.TextField()
    ai_response = models.TextField()
    response_time = models.FloatField(help_text="Response time in seconds")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # API-related fields
    api_success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    
    # Knowledge base usage
    kb_entries_used = models.ManyToManyField(FAQEntry, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Request at {self.timestamp} - Success: {self.api_success}"
