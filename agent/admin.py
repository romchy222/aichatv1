from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import FAQEntry, ChatSession, ChatMessage, RequestLog, AIModelConfig, SystemPrompt, APIKeyConfig, SearchQuery, KnowledgeBaseEntry, ContentFilter, ModerationLog, FileUpload


@admin.register(FAQEntry)
class FAQEntryAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('question', 'answer', 'keywords')
    list_editable = ('is_active',)
    
    fieldsets = (
        (None, {
            'fields': ('question', 'answer', 'category')
        }),
        ('Search & Metadata', {
            'fields': ('keywords', 'is_active')
        }),
    )


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'created_at', 'last_activity')
    list_filter = ('created_at', 'last_activity')
    search_fields = ('session_id', 'user__username')
    readonly_fields = ('session_id', 'created_at', 'last_activity')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'message_type', 'content_preview', 'timestamp')
    list_filter = ('message_type', 'timestamp')
    search_fields = ('content',)
    readonly_fields = ('timestamp',)
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'api_success', 'response_time', 'tokens_used')
    list_filter = ('api_success', 'timestamp')
    search_fields = ('user_message', 'ai_response')
    readonly_fields = ('timestamp',)
    
    fieldsets = (
        (None, {
            'fields': ('session', 'user_message', 'ai_response')
        }),
        ('Performance', {
            'fields': ('response_time', 'tokens_used', 'api_success', 'error_message')
        }),
    )


@admin.register(AIModelConfig)
class AIModelConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_name', 'is_active', 'max_tokens', 'temperature', 'updated_at')
    list_filter = ('is_active', 'model_name', 'updated_at')
    search_fields = ('name', 'model_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Configuration', {
            'fields': ('name', 'model_name', 'is_active')
        }),
        ('Model Parameters', {
            'fields': ('max_tokens', 'temperature', 'top_p', 'repetition_penalty'),
            'description': 'Fine-tune the AI model behavior'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def activate_model(self, request, queryset):
        """Custom action to activate selected model"""
        if queryset.count() > 1:
            self.message_user(request, "Please select only one model to activate.", level='error')
            return
        
        # Deactivate all models
        AIModelConfig.objects.update(is_active=False)
        
        # Activate selected model
        queryset.update(is_active=True)
        model = queryset.first()
        self.message_user(request, f"Model '{model.name}' has been activated successfully!")
    
    activate_model.short_description = "Activate selected model"
    actions = ['activate_model']


@admin.register(SystemPrompt)
class SystemPromptAdmin(admin.ModelAdmin):
    list_display = ('name', 'prompt_type', 'is_active', 'content_preview', 'updated_at')
    list_filter = ('prompt_type', 'is_active', 'updated_at')
    search_fields = ('name', 'content')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'prompt_type', 'is_active')
        }),
        ('Prompt Content', {
            'fields': ('content',),
            'description': 'Enter the system prompt content. Use clear and specific instructions.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def content_preview(self, obj):
        """Show preview of prompt content"""
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'
    
    def activate_prompt(self, request, queryset):
        """Custom action to activate selected prompt"""
        if queryset.count() > 1:
            self.message_user(request, "Please select only one prompt to activate.", level='error')
            return
        
        prompt = queryset.first()
        
        # Deactivate all prompts of the same type
        SystemPrompt.objects.filter(prompt_type=prompt.prompt_type).update(is_active=False)
        
        # Activate selected prompt
        queryset.update(is_active=True)
        self.message_user(request, f"Prompt '{prompt.name}' has been activated successfully!")
    
    activate_prompt.short_description = "Activate selected prompt"
    actions = ['activate_prompt']


@admin.register(APIKeyConfig)
class APIKeyConfigAdmin(admin.ModelAdmin):
    list_display = ('provider', 'api_url', 'is_active', 'max_requests_per_minute', 'updated_at')
    list_filter = ('provider', 'is_active', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('API Configuration', {
            'fields': ('provider', 'api_url', 'is_active', 'max_requests_per_minute')
        }),
        ('Security', {
            'fields': ('api_key',),
            'description': 'API key will be encrypted in production environment'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form to show API key as password field"""
        form = super().get_form(request, obj, **kwargs)
        if 'api_key' in form.base_fields:
            form.base_fields['api_key'].widget.attrs['type'] = 'password'
        return form
    
    def activate_api(self, request, queryset):
        """Custom action to activate selected API configuration"""
        if queryset.count() > 1:
            self.message_user(request, "Please select only one API configuration to activate.", level='error')
            return
        
        api_config = queryset.first()
        
        # Deactivate all API configs for the same provider
        APIKeyConfig.objects.filter(provider=api_config.provider).update(is_active=False)
        
        # Activate selected API config
        queryset.update(is_active=True)
        self.message_user(request, f"API configuration for '{api_config.get_provider_display()}' has been activated!")
    
    activate_api.short_description = "Activate selected API configuration"
    actions = ['activate_api']


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('query_preview', 'language', 'results_found', 'should_add_to_kb', 'added_to_kb', 'created_at')
    list_filter = ('language', 'results_found', 'should_add_to_kb', 'added_to_kb', 'created_at')
    search_fields = ('query', 'ai_response')
    readonly_fields = ('created_at', 'session_id', 'ip_address', 'user_agent')
    
    fieldsets = (
        ('Search Information', {
            'fields': ('query', 'language', 'results_found')
        }),
        ('AI Response', {
            'fields': ('ai_response',),
            'classes': ('collapse',)
        }),
        ('Knowledge Base Status', {
            'fields': ('should_add_to_kb', 'added_to_kb')
        }),
        ('Technical Details', {
            'fields': ('session_id', 'ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def query_preview(self, obj):
        """Show preview of search query"""
        return obj.query[:100] + "..." if len(obj.query) > 100 else obj.query
    query_preview.short_description = 'Query'
    
    def generate_kb_entry(self, request, queryset):
        """Custom action to generate knowledge base entries from search queries"""
        generated_count = 0
        
        for query in queryset:
            if not query.should_add_to_kb or query.added_to_kb:
                continue
                
            # Create KB entry from search query
            kb_entry = KnowledgeBaseEntry.objects.create(
                question=query.query,
                answer=query.ai_response or "Информация уточняется",
                category='general',
                keywords=query.query.lower(),
                source='search_based',
                language=query.language,
                confidence_score=0.7,
                is_verified=False
            )
            
            # Mark as added to KB
            query.added_to_kb = True
            query.save()
            
            generated_count += 1
        
        self.message_user(request, f"Generated {generated_count} knowledge base entries from search queries!")
    
    generate_kb_entry.short_description = "Generate KB entries from selected queries"
    actions = ['generate_kb_entry']


@admin.register(KnowledgeBaseEntry)
class KnowledgeBaseEntryAdmin(admin.ModelAdmin):
    list_display = ('question_preview', 'category', 'language', 'source', 'confidence_score', 'is_verified', 'is_active', 'usage_count', 'created_at')
    list_filter = ('category', 'language', 'source', 'is_verified', 'is_active', 'created_at')
    search_fields = ('question', 'answer', 'keywords')
    list_editable = ('is_active', 'is_verified')
    
    fieldsets = (
        ('Content', {
            'fields': ('question', 'answer', 'category', 'language')
        }),
        ('Metadata', {
            'fields': ('keywords', 'source', 'confidence_score')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified')
        }),
        ('Usage Statistics', {
            'fields': ('usage_count', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('usage_count', 'last_used', 'created_at', 'updated_at')
    
    def question_preview(self, obj):
        """Show preview of question"""
        return obj.question[:80] + "..." if len(obj.question) > 80 else obj.question
    question_preview.short_description = 'Question'
    
    def verify_entry(self, request, queryset):
        """Custom action to verify selected entries"""
        queryset.update(is_verified=True)
        self.message_user(request, f"Verified {queryset.count()} knowledge base entries!")
    
    verify_entry.short_description = "Verify selected entries"
    actions = ['verify_entry']


@admin.register(ContentFilter)
class ContentFilterAdmin(admin.ModelAdmin):
    list_display = ('content_preview', 'filter_type', 'severity', 'language', 'is_active', 'created_at')
    list_filter = ('filter_type', 'severity', 'language', 'is_active', 'applies_to_ai', 'applies_to_faq', 'applies_to_input')
    search_fields = ('content', 'replacement')
    list_editable = ('is_active', 'severity')
    
    fieldsets = (
        ('Filter Configuration', {
            'fields': ('content', 'filter_type', 'severity', 'replacement', 'is_active')
        }),
        ('Application Settings', {
            'fields': ('applies_to_ai', 'applies_to_faq', 'applies_to_input', 'language')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def content_preview(self, obj):
        return f"{obj.content[:30]}..." if len(obj.content) > 30 else obj.content
    content_preview.short_description = 'Content'


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ('original_content_preview', 'action', 'content_type', 'filter_matched', 'created_at')
    list_filter = ('action', 'content_type', 'created_at')
    search_fields = ('original_content', 'modified_content')
    readonly_fields = ('original_content', 'modified_content', 'action', 'filter_matched', 'content_type', 'session_id', 'ip_address', 'created_at')
    
    def original_content_preview(self, obj):
        return f"{obj.original_content[:50]}..." if len(obj.original_content) > 50 else obj.original_content
    original_content_preview.short_description = 'Original Content'
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation of moderation logs
    
    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing of moderation logs
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete logs


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'file_type', 'status', 'file_size_display', 'uploaded_at', 'user', 'session_id')
    list_filter = ('file_type', 'status', 'uploaded_at')
    search_fields = ('original_filename', 'session_id', 'user__username')
    readonly_fields = ('original_filename', 'file_size', 'mime_type', 'uploaded_at', 'processed_at')
    
    fieldsets = (
        ('File Information', {
            'fields': ('file', 'original_filename', 'file_type', 'file_size', 'mime_type')
        }),
        ('Processing Status', {
            'fields': ('status', 'extracted_text', 'analysis_result')
        }),
        ('Session & User', {
            'fields': ('session_id', 'user')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        size = obj.file_size
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = 'File Size'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user')


# Custom admin site customization
admin.site.site_header = "AI Chat Assistant - Super Admin"
admin.site.site_title = "AI Chat Admin"
admin.site.index_title = "System Configuration"
