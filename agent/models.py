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


class AIModelConfig(models.Model):
    """Model for AI model configuration"""
    
    MODEL_CHOICES = [
        ('mistralai/Mistral-7B-Instruct-v0.1', 'Mistral 7B Instruct v0.1'),
        ('mistralai/Mistral-7B-Instruct-v0.2', 'Mistral 7B Instruct v0.2'),
        ('mistralai/Mistral-7B-Instruct-v0.3', 'Mistral 7B Instruct v0.3'),
        ('mistralai/Mixtral-8x7B-Instruct-v0.1', 'Mixtral 8x7B Instruct v0.1'),
        ('mistralai/Mixtral-8x22B-Instruct-v0.1', 'Mixtral 8x22B Instruct v0.1'),
        ('meta-llama/Llama-2-7b-chat-hf', 'Llama 2 7B Chat'),
        ('meta-llama/Llama-2-13b-chat-hf', 'Llama 2 13B Chat'),
        ('meta-llama/Llama-2-70b-chat-hf', 'Llama 2 70B Chat'),
        ('meta-llama/Meta-Llama-3-8B-Instruct', 'Llama 3 8B Instruct'),
        ('meta-llama/Meta-Llama-3-70B-Instruct', 'Llama 3 70B Instruct'),
        ('NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO', 'Nous Hermes 2 Mixtral 8x7B'),
        ('teknium/OpenHermes-2.5-Mistral-7B', 'OpenHermes 2.5 Mistral 7B'),
        ('togethercomputer/RedPajama-INCITE-7B-Chat', 'RedPajama INCITE 7B Chat'),
        ('Qwen/Qwen1.5-7B-Chat', 'Qwen 1.5 7B Chat'),
        ('Qwen/Qwen1.5-14B-Chat', 'Qwen 1.5 14B Chat'),
        ('Qwen/Qwen1.5-72B-Chat', 'Qwen 1.5 72B Chat'),
    ]
    
    name = models.CharField(max_length=100, unique=True, default='default')
    model_name = models.CharField(max_length=200, choices=MODEL_CHOICES, default='mistralai/Mistral-7B-Instruct-v0.1')
    max_tokens = models.IntegerField(default=500, help_text="Maximum tokens for response")
    temperature = models.FloatField(default=0.7, help_text="Temperature for response randomness (0.0-1.0)")
    top_p = models.FloatField(default=0.9, help_text="Top-p sampling parameter (0.0-1.0)")
    repetition_penalty = models.FloatField(default=1.0, help_text="Repetition penalty (1.0 = no penalty)")
    is_active = models.BooleanField(default=False, help_text="Use this configuration")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI Model Configuration"
        verbose_name_plural = "AI Model Configurations"
        ordering = ['-updated_at']
    
    def save(self, *args, **kwargs):
        # Ensure only one configuration is active
        if self.is_active:
            AIModelConfig.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - {self.get_model_name_display()}"


class SystemPrompt(models.Model):
    """Model for system prompts management"""
    
    PROMPT_TYPES = [
        ('system', 'System Prompt'),
        ('assistant', 'Assistant Persona'),
        ('knowledge_base', 'Knowledge Base Context'),
        ('fallback', 'Fallback Response'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    prompt_type = models.CharField(max_length=20, choices=PROMPT_TYPES, default='system')
    content = models.TextField(help_text="The prompt content")
    is_active = models.BooleanField(default=False, help_text="Use this prompt")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "System Prompt"
        verbose_name_plural = "System Prompts"
        ordering = ['prompt_type', '-updated_at']
    
    def save(self, *args, **kwargs):
        # Ensure only one prompt per type is active
        if self.is_active:
            SystemPrompt.objects.filter(prompt_type=self.prompt_type, is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.get_prompt_type_display()})"


class APIKeyConfig(models.Model):
    """Model for API key management"""
    
    API_PROVIDERS = [
        ('together', 'Together.ai'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('cohere', 'Cohere'),
        ('huggingface', 'Hugging Face'),
    ]
    
    provider = models.CharField(max_length=20, choices=API_PROVIDERS, unique=True)
    api_key = models.CharField(max_length=500, help_text="API key (encrypted in production)")
    api_url = models.URLField(help_text="API endpoint URL")
    is_active = models.BooleanField(default=False, help_text="Use this API configuration")
    max_requests_per_minute = models.IntegerField(default=60, help_text="Rate limiting")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "API Key Configuration"
        verbose_name_plural = "API Key Configurations"
        ordering = ['provider']
    
    def save(self, *args, **kwargs):
        # Ensure only one API config per provider is active
        if self.is_active:
            APIKeyConfig.objects.filter(provider=self.provider, is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_provider_display()} API"
