from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


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
    project = models.ForeignKey('ChatProject', on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    title = models.CharField(max_length=200, blank=True, help_text="Название беседы")
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"Session {self.session_id} - {self.created_at}"
    
    def get_title(self):
        """Get session title or generate from first message"""
        if self.title:
            return self.title
        first_message = self.messages.filter(message_type='user').first()
        if first_message:
            return first_message.content[:50] + "..." if len(first_message.content) > 50 else first_message.content
        return f"Сессия {self.session_id[:8]}"


class ChatMessage(models.Model):
    """Model for storing individual chat messages"""
    
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
        ('voice', 'Voice'),
        ('image', 'Image'),
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
    kb_entries_used_new = models.ManyToManyField('KnowledgeBaseEntry', blank=True, related_name='request_logs')
    
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


class SearchQuery(models.Model):
    """Model to store search queries for knowledge base enhancement"""
    
    query = models.TextField()
    language = models.CharField(max_length=10, default='ru')  # ru, kk, en
    results_found = models.BooleanField(default=False)
    ai_response = models.TextField(blank=True, null=True)
    should_add_to_kb = models.BooleanField(default=False)
    added_to_kb = models.BooleanField(default=False)
    session_id = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Search Query'
        verbose_name_plural = 'Search Queries'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Search: {self.query[:50]}..."


class ContentFilter(models.Model):
    """Model to store content filtering rules and banned words"""
    
    FILTER_TYPE_CHOICES = [
        ('banned_word', 'Запрещенное слово'),
        ('pattern', 'Шаблон (regex)'),
        ('phrase', 'Запрещенная фраза'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Низкая (предупреждение)'),
        ('medium', 'Средняя (цензура)'),
        ('high', 'Высокая (блокировка)'),
    ]
    
    filter_type = models.CharField(max_length=20, choices=FILTER_TYPE_CHOICES, default='banned_word')
    content = models.TextField(help_text="Слово, фраза или regex-шаблон для фильтрации")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    replacement = models.CharField(max_length=200, blank=True, help_text="Замена для цензурируемого контента (по умолчанию: ***)")
    is_active = models.BooleanField(default=True)
    applies_to_ai = models.BooleanField(default=True, help_text="Применять к ответам AI")
    applies_to_faq = models.BooleanField(default=True, help_text="Применять к результатам поиска FAQ")
    applies_to_input = models.BooleanField(default=True, help_text="Применять к пользовательскому вводу")
    language = models.CharField(max_length=10, default='all', help_text="Язык (ru/en/kk/all)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Content Filter'
        verbose_name_plural = 'Content Filters'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.get_filter_type_display()}: {self.content[:30]}..."


class ModerationLog(models.Model):
    """Model to log content moderation actions"""
    
    ACTION_CHOICES = [
        ('censored', 'Цензурировано'),
        ('blocked', 'Заблокировано'),
        ('warned', 'Предупреждение'),
    ]
    
    original_content = models.TextField()
    modified_content = models.TextField(blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    filter_matched = models.ForeignKey(ContentFilter, on_delete=models.SET_NULL, null=True)
    content_type = models.CharField(max_length=20, help_text="ai_response/faq_result/user_input")
    session_id = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Moderation Log'
        verbose_name_plural = 'Moderation Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_action_display()}: {self.original_content[:30]}..."


class FileUpload(models.Model):
    """Model for handling file uploads and processing"""
    
    FILE_TYPE_CHOICES = [
        ('image', 'Изображение'),
        ('document', 'Документ'),
        ('spreadsheet', 'Таблица'),
        ('pdf', 'PDF'),
        ('text', 'Текстовый файл'),
        ('other', 'Другое'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает обработки'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Обработан'),
        ('failed', 'Ошибка'),
    ]
    
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other')
    file_size = models.BigIntegerField()  # Size in bytes
    mime_type = models.CharField(max_length=100, blank=True)
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    extracted_text = models.TextField(blank=True, help_text="Извлеченный из файла текст")
    analysis_result = models.JSONField(blank=True, null=True, help_text="Результат анализа файла")
    
    # Session info
    session_id = models.CharField(max_length=100, blank=True, null=True)
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, blank=True, null=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'File Upload'
        verbose_name_plural = 'File Uploads'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.original_filename} ({self.get_file_type_display()})"
    
    def get_file_extension(self):
        """Get file extension"""
        return self.original_filename.split('.')[-1].lower() if '.' in self.original_filename else ''
    
    def is_image(self):
        """Check if file is an image"""
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']
        return self.get_file_extension() in image_extensions
    
    def is_document(self):
        """Check if file is a document"""
        doc_extensions = ['doc', 'docx', 'txt', 'rtf', 'odt']
        return self.get_file_extension() in doc_extensions
    
    def is_spreadsheet(self):
        """Check if file is a spreadsheet"""
        sheet_extensions = ['xls', 'xlsx', 'csv', 'ods']
        return self.get_file_extension() in sheet_extensions
    
    def is_pdf(self):
        """Check if file is a PDF"""
        return self.get_file_extension() == 'pdf'


class KnowledgeBaseEntry(models.Model):
    """Model for auto-generated knowledge base entries"""
    
    CATEGORY_CHOICES = [
        ('schedules', 'Расписание'),
        ('documents', 'Документы'),
        ('scholarships', 'Стипендии'),
        ('exams', 'Экзамены'),
        ('administration', 'Администрация'),
        ('general', 'Общие'),
        ('fees', 'Оплата'),
        ('dormitory', 'Общежитие'),
        ('library', 'Библиотека'),
        ('services', 'Услуги'),
    ]
    
    SOURCE_CHOICES = [
        ('manual', 'Ручное добавление'),
        ('ai_generated', 'Создано AI'),
        ('search_based', 'На основе поиска'),
    ]
    
    question = models.TextField()
    answer = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    keywords = models.TextField(help_text="Ключевые слова для поиска, разделенные пробелами")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    language = models.CharField(max_length=10, default='ru')  # ru, kk, en
    confidence_score = models.FloatField(default=0.0)  # AI confidence in the answer
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)  # Admin verification
    usage_count = models.IntegerField(default=0)
    last_used = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Knowledge Base Entry'
        verbose_name_plural = 'Knowledge Base Entries'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.question[:50]}..."
    
    def increment_usage(self):
        """Increment usage count and update last used timestamp"""
        from django.utils import timezone
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])


class UserProfile(models.Model):
    """Extended user profile for personalization"""
    
    LANGUAGE_CHOICES = [
        ('ru', 'Русский'),
        ('kk', 'Қазақша'),
        ('en', 'English'),
    ]
    
    ROLE_CHOICES = [
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
        ('staff', 'Сотрудник'),
        ('admin', 'Администратор'),
        ('guest', 'Гость'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True, null=True, blank=True)  # For anonymous users
    
    # Personal preferences
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='ru')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guest')
    
    # Academic information
    faculty = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    course_year = models.IntegerField(null=True, blank=True, help_text="Курс обучения")
    group_number = models.CharField(max_length=50, blank=True)
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    deadline_reminders = models.BooleanField(default=True)
    system_announcements = models.BooleanField(default=True)
    
    # Usage statistics
    total_messages = models.IntegerField(default=0)
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-last_active']
    
    def __str__(self):
        if self.user:
            return f"{self.user.username} ({self.get_role_display()})"
        return f"Сессия {self.session_id} ({self.get_role_display()})"


class ChatProject(models.Model):
    """Model for organizing chats into projects/topics"""
    
    PROJECT_TYPES = [
        ('academic', 'Учёба'),
        ('research', 'Исследования'),
        ('personal', 'Личное'),
        ('work', 'Работа'),
        ('general', 'Общее'),
    ]
    
    name = models.CharField(max_length=100, help_text="Название проекта")
    description = models.TextField(blank=True, help_text="Описание проекта")
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPES, default='general')
    color = models.CharField(max_length=7, default='#0D1B2A', help_text="Цвет темы (hex)")
    icon = models.CharField(max_length=20, default='fas fa-folder', help_text="FontAwesome иконка")
    
    # Project settings
    custom_prompt = models.TextField(blank=True, help_text="Специальные инструкции для AI")
    allowed_file_types = models.JSONField(default=list, help_text="Разрешенные типы файлов")
    max_context_messages = models.IntegerField(default=20, help_text="Максимум сообщений в контексте")
    
    # Owner and sharing
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    is_shared = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Chat Project'
        verbose_name_plural = 'Chat Projects'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_project_type_display()})"


class VoiceMessage(models.Model):
    """Model for storing voice messages and transcriptions"""
    
    STATUS_CHOICES = [
        ('uploading', 'Загружается'),
        ('transcribing', 'Распознается'),
        ('completed', 'Готово'),
        ('failed', 'Ошибка'),
    ]
    
    chat_message = models.OneToOneField(ChatMessage, on_delete=models.CASCADE, related_name='voice_data')
    audio_file = models.FileField(upload_to='voice/%Y/%m/%d/')
    duration = models.FloatField(help_text="Длительность в секундах")
    transcription = models.TextField(blank=True, help_text="Расшифровка речи")
    confidence = models.FloatField(default=0.0, help_text="Уверенность распознавания (0-1)")
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploading')
    error_message = models.TextField(blank=True)
    
    # Voice characteristics (optional)
    detected_language = models.CharField(max_length=10, blank=True)
    emotion = models.CharField(max_length=20, blank=True, help_text="Определенная эмоция")
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Voice Message'
        verbose_name_plural = 'Voice Messages'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Голосовое сообщение {self.duration:.1f}с"


class MessageAttachment(models.Model):
    """Model for attachments to chat messages (images, documents, etc.)"""
    
    ATTACHMENT_TYPES = [
        ('image', 'Изображение'),
        ('document', 'Документ'),
        ('audio', 'Аудио'),
        ('video', 'Видео'),
        ('file', 'Файл'),
    ]
    
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/%Y/%m/%d/')
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES)
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    
    # AI analysis results
    analysis_result = models.JSONField(blank=True, null=True, help_text="Результат анализа AI")
    extracted_text = models.TextField(blank=True, help_text="Извлеченный текст")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Message Attachment'
        verbose_name_plural = 'Message Attachments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.original_filename} ({self.get_attachment_type_display()})"


class ConversationSummary(models.Model):
    """Model for storing AI-generated conversation summaries"""
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='summaries')
    project = models.ForeignKey(ChatProject, on_delete=models.SET_NULL, null=True, blank=True)
    
    summary = models.TextField(help_text="Краткое содержание беседы")
    key_topics = models.JSONField(default=list, help_text="Основные темы обсуждения")
    action_items = models.JSONField(default=list, help_text="Задачи и действия")
    
    # Summary metadata
    message_count = models.IntegerField(default=0)
    date_range_start = models.DateTimeField()
    date_range_end = models.DateTimeField()
    
    # AI generation info
    generated_by = models.CharField(max_length=50, default='ai')
    confidence_score = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Conversation Summary'
        verbose_name_plural = 'Conversation Summaries'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Сводка {self.session.session_id[:8]} ({self.message_count} сообщений)"


class UserMood(models.Model):
    """Model for tracking user mood and emotional state"""
    
    MOOD_CHOICES = [
        ('happy', '😊 Радостное'),
        ('neutral', '😐 Нейтральное'),
        ('sad', '😢 Грустное'),
        ('angry', '😠 Злое'),
        ('excited', '🤩 Взволнованное'),
        ('confused', '😕 Смущенное'),
        ('frustrated', '😤 Расстроенное'),
        ('calm', '😌 Спокойное'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='mood_tracking')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES)
    confidence = models.FloatField(default=0.0, help_text="Уверенность определения (0-1)")
    
    # Context
    message_trigger = models.ForeignKey(ChatMessage, on_delete=models.SET_NULL, null=True, blank=True)
    detected_keywords = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'User Mood'
        verbose_name_plural = 'User Moods'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_mood_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class Notification(models.Model):
    """System notifications and reminders"""
    
    TYPE_CHOICES = [
        ('deadline', 'Дедлайн'),
        ('exam', 'Экзамен'),
        ('announcement', 'Объявление'),
        ('reminder', 'Напоминание'),
        ('system', 'Системное'),
        ('achievement', 'Достижение'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Targeting
    target_roles = models.JSONField(default=list, help_text="Список ролей для уведомления")
    target_faculties = models.JSONField(default=list, help_text="Список факультетов")
    target_courses = models.JSONField(default=list, help_text="Список курсов")
    target_users = models.ManyToManyField(User, blank=True, help_text="Конкретные пользователи")
    
    # Scheduling
    scheduled_for = models.DateTimeField(null=True, blank=True, help_text="Запланировать отправку")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Срок действия")
    
    # Status
    is_active = models.BooleanField(default=True)
    is_sent = models.BooleanField(default=False)
    sent_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_notifications')
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_priority_display()})"


class UserNotification(models.Model):
    """Individual user notification tracking"""
    
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'User Notification'
        verbose_name_plural = 'User Notifications'
        unique_together = ['user_profile', 'notification']
        ordering = ['-delivered_at']
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class Analytics(models.Model):
    """System analytics and usage statistics"""
    
    METRIC_TYPES = [
        ('daily_users', 'Дневная активность'),
        ('message_count', 'Количество сообщений'),
        ('response_time', 'Время ответа'),
        ('popular_topics', 'Популярные темы'),
        ('error_rate', 'Частота ошибок'),
        ('satisfaction', 'Удовлетворенность'),
    ]
    
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES)
    metric_value = models.FloatField()
    metadata = models.JSONField(default=dict, help_text="Дополнительная информация")
    
    date_recorded = models.DateField()
    hour_recorded = models.IntegerField(null=True, blank=True, help_text="Час дня (0-23)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Analytics'
        verbose_name_plural = 'Analytics'
        unique_together = ['metric_type', 'date_recorded', 'hour_recorded']
        ordering = ['-date_recorded', '-hour_recorded']
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.metric_value} ({self.date_recorded})"


class EventSchedule(models.Model):
    """University events, deadlines, and important dates"""
    
    EVENT_TYPES = [
        ('exam', 'Экзамен'),
        ('deadline', 'Дедлайн'),
        ('lecture', 'Лекция'),
        ('seminar', 'Семинар'),
        ('holiday', 'Праздник'),
        ('registration', 'Регистрация'),
        ('meeting', 'Собрание'),
        ('other', 'Другое'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='other')
    
    # Date and time
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)
    
    # Location
    location = models.CharField(max_length=200, blank=True)
    room_number = models.CharField(max_length=50, blank=True)
    
    # Targeting
    target_faculties = models.JSONField(default=list)
    target_courses = models.JSONField(default=list)
    target_groups = models.JSONField(default=list)
    is_public = models.BooleanField(default=True)
    
    # Reminders
    reminder_days_before = models.IntegerField(default=1, help_text="За сколько дней напомнить")
    reminder_sent = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_cancelled = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'Event Schedule'
        verbose_name_plural = 'Event Schedules'
        ordering = ['start_datetime']
    
    def __str__(self):
        return f"{self.title} ({self.start_datetime.strftime('%d.%m.%Y %H:%M')})"
    
    def is_upcoming(self):
        """Check if event is upcoming"""
        return self.start_datetime > timezone.now()
    
    def needs_reminder(self):
        """Check if reminder should be sent"""
        if self.reminder_sent or not self.is_active or self.is_cancelled:
            return False
        
        reminder_time = self.start_datetime - timezone.timedelta(days=self.reminder_days_before)
        return timezone.now() >= reminder_time
