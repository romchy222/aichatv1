"""
Analytics module for tracking system usage and generating insights
"""

from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from collections import defaultdict
import json

from .models import (
    ChatMessage, RequestLog, Analytics, UserProfile, 
    FAQEntry, SearchQuery, EventSchedule, Notification
)


class AnalyticsManager:
    """Manager for analytics collection and reporting"""
    
    def __init__(self):
        self.today = timezone.now().date()
        self.now = timezone.now()
    
    def collect_daily_metrics(self):
        """Collect and store daily metrics"""
        metrics = {
            'daily_users': self._get_daily_users(),
            'message_count': self._get_daily_messages(),
            'response_time': self._get_average_response_time(),
            'popular_topics': self._get_popular_topics(),
            'error_rate': self._get_error_rate(),
        }
        
        for metric_type, value in metrics.items():
            if value is not None:
                Analytics.objects.update_or_create(
                    metric_type=metric_type,
                    date_recorded=self.today,
                    hour_recorded=None,
                    defaults={'metric_value': value}
                )
        
        return metrics
    
    def collect_hourly_metrics(self):
        """Collect and store hourly metrics"""
        hour = self.now.hour
        
        metrics = {
            'message_count': self._get_hourly_messages(hour),
            'response_time': self._get_hourly_response_time(hour),
        }
        
        for metric_type, value in metrics.items():
            if value is not None:
                Analytics.objects.update_or_create(
                    metric_type=metric_type,
                    date_recorded=self.today,
                    hour_recorded=hour,
                    defaults={'metric_value': value}
                )
        
        return metrics
    
    def _get_daily_users(self):
        """Get number of unique users today"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Count unique session IDs from today's messages
        unique_sessions = ChatMessage.objects.filter(
            timestamp__gte=today_start
        ).values('session__session_id').distinct().count()
        
        return unique_sessions
    
    def _get_daily_messages(self):
        """Get total messages today"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        return ChatMessage.objects.filter(
            timestamp__gte=today_start
        ).count()
    
    def _get_hourly_messages(self, hour):
        """Get messages in specific hour today"""
        hour_start = timezone.now().replace(hour=hour, minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        
        return ChatMessage.objects.filter(
            timestamp__gte=hour_start,
            timestamp__lt=hour_end
        ).count()
    
    def _get_average_response_time(self):
        """Get average AI response time today"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        avg_time = RequestLog.objects.filter(
            timestamp__gte=today_start,
            response_time__isnull=False
        ).aggregate(avg_time=Avg('response_time'))['avg_time']
        
        return avg_time if avg_time else 0
    
    def _get_hourly_response_time(self, hour):
        """Get average response time for specific hour"""
        hour_start = timezone.now().replace(hour=hour, minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        
        avg_time = RequestLog.objects.filter(
            timestamp__gte=hour_start,
            timestamp__lt=hour_end,
            response_time__isnull=False
        ).aggregate(avg_time=Avg('response_time'))['avg_time']
        
        return avg_time if avg_time else 0
    
    def _get_popular_topics(self):
        """Get most popular FAQ topics today"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get most searched topics
        popular_searches = SearchQuery.objects.filter(
            created_at__gte=today_start
        ).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Convert to score (number of unique searches)
        return len(popular_searches)
    
    def _get_error_rate(self):
        """Get error rate today"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        total_requests = RequestLog.objects.filter(timestamp__gte=today_start).count()
        failed_requests = RequestLog.objects.filter(
            timestamp__gte=today_start,
            status_code__gte=400
        ).count()
        
        if total_requests == 0:
            return 0
        
        return (failed_requests / total_requests) * 100
    
    def get_dashboard_data(self, days=7):
        """Get comprehensive dashboard data"""
        end_date = self.today
        start_date = end_date - timedelta(days=days-1)
        
        # Daily metrics for the period
        daily_metrics = Analytics.objects.filter(
            date_recorded__gte=start_date,
            date_recorded__lte=end_date,
            hour_recorded__isnull=True
        ).order_by('date_recorded')
        
        # Organize metrics by type
        metrics_by_type = defaultdict(list)
        for metric in daily_metrics:
            metrics_by_type[metric.metric_type].append({
                'date': metric.date_recorded.strftime('%Y-%m-%d'),
                'value': metric.metric_value
            })
        
        # Get current stats
        current_stats = {
            'total_users': UserProfile.objects.count(),
            'total_messages': ChatMessage.objects.count(),
            'active_sessions_today': self._get_daily_users(),
            'avg_response_time': self._get_average_response_time(),
            'total_faq_entries': FAQEntry.objects.filter(is_active=True).count(),
            'upcoming_events': EventSchedule.objects.filter(
                start_datetime__gte=timezone.now(),
                is_active=True,
                is_cancelled=False
            ).count()
        }
        
        # Popular searches
        popular_searches = SearchQuery.objects.filter(
            created_at__gte=start_date
        ).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Hourly activity today
        hourly_activity = Analytics.objects.filter(
            date_recorded=self.today,
            metric_type='message_count',
            hour_recorded__isnull=False
        ).order_by('hour_recorded')
        
        hourly_data = []
        for hour in range(24):
            activity = hourly_activity.filter(hour_recorded=hour).first()
            hourly_data.append({
                'hour': hour,
                'messages': activity.metric_value if activity else 0
            })
        
        return {
            'period': f"{start_date} to {end_date}",
            'daily_metrics': dict(metrics_by_type),
            'current_stats': current_stats,
            'popular_searches': list(popular_searches),
            'hourly_activity': hourly_data,
            'generated_at': timezone.now().isoformat()
        }
    
    def get_user_insights(self, days=30):
        """Get user behavior insights"""
        end_date = self.today
        start_date = end_date - timedelta(days=days-1)
        
        # User role distribution
        role_distribution = UserProfile.objects.values('role').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Language preferences
        language_distribution = UserProfile.objects.values('preferred_language').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Most active users
        active_users = UserProfile.objects.filter(
            last_active__gte=start_date
        ).order_by('-total_messages')[:10]
        
        # Message patterns by hour
        message_patterns = ChatMessage.objects.filter(
            timestamp__gte=start_date
        ).extra(
            select={'hour': 'EXTRACT(hour FROM timestamp)'}
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        return {
            'period': f"{start_date} to {end_date}",
            'role_distribution': list(role_distribution),
            'language_distribution': list(language_distribution),
            'active_users': [
                {
                    'id': profile.id,
                    'role': profile.get_role_display(),
                    'messages': profile.total_messages,
                    'last_active': profile.last_active.strftime('%Y-%m-%d %H:%M')
                }
                for profile in active_users
            ],
            'message_patterns': list(message_patterns),
            'generated_at': timezone.now().isoformat()
        }


class NotificationManager:
    """Manager for handling notifications and reminders"""
    
    def process_scheduled_notifications(self):
        """Process and send scheduled notifications"""
        now = timezone.now()
        
        # Get notifications that should be sent now
        due_notifications = Notification.objects.filter(
            is_active=True,
            is_sent=False,
            scheduled_for__lte=now
        ).exclude(
            expires_at__lt=now
        )
        
        sent_count = 0
        for notification in due_notifications:
            if self._send_notification(notification):
                notification.is_sent = True
                notification.sent_count = self._get_target_count(notification)
                notification.save()
                sent_count += 1
        
        return sent_count
    
    def process_event_reminders(self):
        """Process and send event reminders"""
        events_needing_reminders = EventSchedule.objects.filter(
            is_active=True,
            is_cancelled=False,
            reminder_sent=False
        )
        
        sent_count = 0
        for event in events_needing_reminders:
            if event.needs_reminder():
                if self._send_event_reminder(event):
                    event.reminder_sent = True
                    event.save()
                    sent_count += 1
        
        return sent_count
    
    def _send_notification(self, notification):
        """Send notification to target users"""
        target_profiles = self._get_target_profiles(notification)
        
        for profile in target_profiles:
            # Create user notification record
            user_notification, created = UserNotification.objects.get_or_create(
                user_profile=profile,
                notification=notification
            )
            
            # Here you would integrate with actual notification services
            # (email, SMS, push notifications, etc.)
            # For now, we just create the database record
        
        return True
    
    def _send_event_reminder(self, event):
        """Send event reminder notification"""
        # Create a notification for the event
        notification = Notification.objects.create(
            title=f"Напоминание: {event.title}",
            message=f"Событие '{event.title}' состоится {event.start_datetime.strftime('%d.%m.%Y в %H:%M')}",
            notification_type='reminder',
            priority='medium',
            target_faculties=event.target_faculties,
            target_courses=event.target_courses,
            is_active=True,
            is_sent=False
        )
        
        return self._send_notification(notification)
    
    def _get_target_profiles(self, notification):
        """Get user profiles that should receive notification"""
        profiles = UserProfile.objects.filter(
            system_announcements=True  # Respect user preferences
        )
        
        # Filter by roles
        if notification.target_roles:
            profiles = profiles.filter(role__in=notification.target_roles)
        
        # Filter by faculties
        if notification.target_faculties:
            profiles = profiles.filter(faculty__in=notification.target_faculties)
        
        # Filter by courses
        if notification.target_courses:
            profiles = profiles.filter(course_year__in=notification.target_courses)
        
        return profiles
    
    def _get_target_count(self, notification):
        """Get count of target users for notification"""
        return self._get_target_profiles(notification).count()
    
    def get_user_notifications(self, user_profile, unread_only=False):
        """Get notifications for a specific user"""
        notifications = UserNotification.objects.filter(
            user_profile=user_profile
        ).select_related('notification')
        
        if unread_only:
            notifications = notifications.filter(is_read=False)
        
        return notifications.order_by('-delivered_at')