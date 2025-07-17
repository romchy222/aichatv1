from django.contrib import admin
from .models import FAQEntry, ChatSession, ChatMessage, RequestLog


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
