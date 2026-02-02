# Content Moderation System

"""
Moderation Features to Implement:

1. Automated Content Filtering
   - Profanity filter
   - Spam detection
   - Inappropriate content detection
   - Link validation

2. User Reporting System
   - Report posts and comments
   - Report users for violations
   - Categorized reporting reasons
   - Anonymous reporting option

3. Moderation Queue
   - Flagged content review
   - Moderator actions (approve, reject, edit)
   - Escalation system
   - Moderation history

4. User Management
   - Warning system
   - Temporary suspensions
   - Permanent bans
   - Appeal process
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import re

class ModerationRule(models.Model):
    RULE_TYPES = [
        ('profanity', 'Profanity Filter'),
        ('spam', 'Spam Detection'),
        ('link', 'Link Validation'),
        ('length', 'Content Length'),
        ('frequency', 'Posting Frequency'),
    ]
    
    name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    pattern = models.TextField()  # Regex pattern or JSON config
    action = models.CharField(max_length=20, choices=[
        ('flag', 'Flag for Review'),
        ('auto_reject', 'Auto Reject'),
        ('warn', 'Warn User'),
        ('suspend', 'Suspend User'),
    ])
    is_active = models.BooleanField(default=True)
    severity = models.IntegerField(default=1)  # 1-5 severity level
    
    def __str__(self):
        return self.name

class ContentReport(models.Model):
    REPORT_REASONS = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('hate_speech', 'Hate Speech'),
        ('inappropriate', 'Inappropriate Content'),
        ('misinformation', 'Misinformation'),
        ('copyright', 'Copyright Violation'),
        ('other', 'Other'),
    ]
    
    CONTENT_TYPES = [
        ('post', 'Post'),
        ('comment', 'Comment'),
        ('user', 'User'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    object_id = models.PositiveIntegerField()
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Moderation fields
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('escalated', 'Escalated'),
    ], default='pending')
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    moderator_notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Report: {self.reason} - {self.content_type} {self.object_id}"

class ModerationAction(models.Model):
    ACTION_TYPES = [
        ('warning', 'Warning'),
        ('content_removal', 'Content Removal'),
        ('content_edit', 'Content Edit'),
        ('temporary_suspension', 'Temporary Suspension'),
        ('permanent_ban', 'Permanent Ban'),
        ('account_restriction', 'Account Restriction'),
    ]
    
    moderator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moderation_actions')
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moderation_received')
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    reason = models.TextField()
    duration = models.DurationField(null=True, blank=True)  # For temporary actions
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Related content
    content_type = models.CharField(max_length=10, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if self.duration and not self.expires_at:
            self.expires_at = timezone.now() + self.duration
        super().save(*args, **kwargs)
    
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def __str__(self):
        return f"{self.action_type} - {self.target_user.username}"

class UserWarning(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='warnings')
    moderator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='warnings_issued')
    reason = models.TextField()
    severity = models.IntegerField(default=1)  # 1-5 severity level
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Warning for {self.user.username}: {self.reason[:50]}"

class ContentFilter:
    """Automated content filtering system"""
    
    @staticmethod
    def check_profanity(text):
        """Check for profanity in text"""
        profanity_words = [
            # Add your profanity word list here
            'badword1', 'badword2', 'badword3'
        ]
        
        text_lower = text.lower()
        found_words = []
        
        for word in profanity_words:
            if word in text_lower:
                found_words.append(word)
        
        return found_words
    
    @staticmethod
    def check_spam(text, user):
        """Check for spam patterns"""
        spam_indicators = []
        
        # Check for excessive links
        link_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        links = re.findall(link_pattern, text)
        if len(links) > 3:
            spam_indicators.append('excessive_links')
        
        # Check for repeated characters
        if re.search(r'(.)\1{4,}', text):
            spam_indicators.append('repeated_characters')
        
        # Check for excessive caps
        caps_ratio = sum(1 for c in text if c.isupper()) / len(text) if text else 0
        if caps_ratio > 0.7 and len(text) > 10:
            spam_indicators.append('excessive_caps')
        
        # Check posting frequency
        from .models import Post, Comment
        recent_posts = Post.objects.filter(
            author=user,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        
        recent_comments = Comment.objects.filter(
            author=user,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        
        if recent_posts + recent_comments > 10:
            spam_indicators.append('high_frequency')
        
        return spam_indicators
    
    @staticmethod
    def moderate_content(text, user, content_type='post'):
        """Main content moderation function"""
        issues = []
        
        # Check profanity
        profanity = ContentFilter.check_profanity(text)
        if profanity:
            issues.append({
                'type': 'profanity',
                'severity': 3,
                'details': profanity
            })
        
        # Check spam
        spam_indicators = ContentFilter.check_spam(text, user)
        if spam_indicators:
            issues.append({
                'type': 'spam',
                'severity': 2,
                'details': spam_indicators
            })
        
        # Determine action based on issues
        max_severity = max([issue['severity'] for issue in issues]) if issues else 0
        
        if max_severity >= 4:
            return {'action': 'reject', 'issues': issues}
        elif max_severity >= 3:
            return {'action': 'flag', 'issues': issues}
        elif max_severity >= 2:
            return {'action': 'warn', 'issues': issues}
        else:
            return {'action': 'approve', 'issues': []}

# Moderation utility functions
def create_moderation_report(reporter, reported_user, content_type, object_id, reason, description=''):
    """Create a new moderation report"""
    report = ContentReport.objects.create(
        reporter=reporter,
        reported_user=reported_user,
        content_type=content_type,
        object_id=object_id,
        reason=reason,
        description=description
    )
    
    # Auto-escalate if user has multiple recent reports
    recent_reports = ContentReport.objects.filter(
        reported_user=reported_user,
        created_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    
    if recent_reports >= 3:
        report.status = 'escalated'
        report.save()
    
    return report

def issue_warning(moderator, user, reason, severity=1):
    """Issue a warning to a user"""
    warning = UserWarning.objects.create(
        user=user,
        moderator=moderator,
        reason=reason,
        severity=severity
    )
    
    # Check if user should be suspended based on warning count
    warning_count = UserWarning.objects.filter(
        user=user,
        created_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).count()
    
    if warning_count >= 3:
        # Auto-suspend for 24 hours
        ModerationAction.objects.create(
            moderator=moderator,
            target_user=user,
            action_type='temporary_suspension',
            reason=f'Automatic suspension due to {warning_count} warnings',
            duration=timezone.timedelta(hours=24)
        )
    
    return warning