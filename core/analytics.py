# Analytics Dashboard

"""
Analytics Features to Add:

1. User Analytics
   - Post engagement rates
   - Comment activity trends
   - Karma growth over time
   - Most popular posts

2. Community Analytics
   - Daily active users
   - Post creation trends
   - Comment engagement rates
   - Top content categories

3. Admin Dashboard
   - User growth metrics
   - Content moderation stats
   - System performance metrics
   - Popular hashtags/topics

4. Data Visualization
   - Charts and graphs
   - Real-time metrics
   - Exportable reports
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class UserAnalytics(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_posts = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    total_likes_received = models.PositiveIntegerField(default=0)
    total_likes_given = models.PositiveIntegerField(default=0)
    avg_engagement_rate = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def calculate_engagement_rate(self):
        """Calculate user's average engagement rate"""
        if self.total_posts == 0:
            return 0.0
        return (self.total_likes_received + self.total_comments) / self.total_posts
    
    def update_analytics(self):
        """Update user analytics from actual data"""
        from .models import Post, Comment, Like
        
        self.total_posts = Post.objects.filter(author=self.user).count()
        self.total_comments = Comment.objects.filter(author=self.user).count()
        
        # Count likes received on user's posts and comments
        post_likes = Like.objects.filter(
            content_type='post',
            object_id__in=Post.objects.filter(author=self.user).values_list('id', flat=True)
        ).count()
        
        comment_likes = Like.objects.filter(
            content_type='comment',
            object_id__in=Comment.objects.filter(author=self.user).values_list('id', flat=True)
        ).count()
        
        self.total_likes_received = post_likes + comment_likes
        self.total_likes_given = Like.objects.filter(user=self.user).count()
        self.avg_engagement_rate = self.calculate_engagement_rate()
        self.save()

class DailyStats(models.Model):
    date = models.DateField(unique=True)
    new_users = models.PositiveIntegerField(default=0)
    new_posts = models.PositiveIntegerField(default=0)
    new_comments = models.PositiveIntegerField(default=0)
    total_likes = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
    
    @classmethod
    def generate_daily_stats(cls, date=None):
        """Generate stats for a specific date"""
        if date is None:
            date = timezone.now().date()
        
        from .models import Post, Comment, Like
        
        stats, created = cls.objects.get_or_create(date=date)
        
        # Count new registrations
        stats.new_users = User.objects.filter(date_joined__date=date).count()
        
        # Count new posts
        stats.new_posts = Post.objects.filter(created_at__date=date).count()
        
        # Count new comments
        stats.new_comments = Comment.objects.filter(created_at__date=date).count()
        
        # Count total likes
        stats.total_likes = Like.objects.filter(created_at__date=date).count()
        
        # Count active users (posted, commented, or liked)
        active_user_ids = set()
        active_user_ids.update(Post.objects.filter(created_at__date=date).values_list('author_id', flat=True))
        active_user_ids.update(Comment.objects.filter(created_at__date=date).values_list('author_id', flat=True))
        active_user_ids.update(Like.objects.filter(created_at__date=date).values_list('user_id', flat=True))
        
        stats.active_users = len(active_user_ids)
        stats.save()
        
        return stats