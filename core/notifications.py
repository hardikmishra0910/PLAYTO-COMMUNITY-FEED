# Real-time Notifications System

"""
Notification Features to Implement:

1. In-App Notifications
   - New likes on your posts/comments
   - New replies to your comments
   - New followers
   - Karma milestones reached

2. WebSocket Integration
   - Real-time notification delivery
   - Live comment updates
   - Real-time like counts

3. Email Notifications
   - Daily/weekly digest
   - Important activity alerts
   - Customizable preferences

4. Push Notifications (PWA)
   - Browser push notifications
   - Mobile app notifications
"""

from django.db import models
from django.contrib.auth.models import User

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('like_post', 'Post Liked'),
        ('like_comment', 'Comment Liked'),
        ('new_comment', 'New Comment'),
        ('new_reply', 'New Reply'),
        ('new_follower', 'New Follower'),
        ('karma_milestone', 'Karma Milestone'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Generic foreign key for linking to any model
    content_type = models.CharField(max_length=50, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message}"