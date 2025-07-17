from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import FAQEntry, ChatSession, ChatMessage, RequestLog, AIModelConfig, SystemPrompt, APIKeyConfig


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


# Custom admin site customization
admin.site.site_header = "AI Chat Assistant - Super Admin"
admin.site.site_title = "AI Chat Admin"
admin.site.index_title = "System Configuration"
