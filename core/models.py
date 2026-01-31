from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
import os


def post_media_upload_path(instance, filename):
    """Generate upload path for post media files"""
    return f'posts/{instance.author.username}/{filename}'


class Post(models.Model):
    """
    Post model with denormalized counts for performance and media support.
    Counts are updated via signals to maintain consistency.
    """
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    
    # Media fields
    image = models.ImageField(upload_to=post_media_upload_path, null=True, blank=True)
    video = models.FileField(upload_to=post_media_upload_path, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Denormalized counts for performance - updated via signals
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['author']),
        ]
    
    def __str__(self):
        return f"Post by {self.author.username}: {self.content[:50]}..."
    
    @property
    def has_media(self):
        """Check if post has any media attached"""
        return bool(self.image or self.video)
    
    def get_media_type(self):
        """Get the type of media attached"""
        if self.image:
            return 'image'
        elif self.video:
            return 'video'
        return None


class Comment(models.Model):
    """
    Threaded comments using adjacency list pattern.
    
    This approach stores parent_id directly on each comment, allowing:
    1. Simple insertion of new comments/replies
    2. Efficient tree traversal with prefetch_related
    3. Easy depth calculation and ordering
    
    Alternative approaches considered:
    - django-mptt: More complex, better for frequent tree operations
    - Materialized path: Good for deep trees, more storage overhead
    - Nested sets: Complex updates, better for read-heavy workloads
    
    Adjacency list chosen for simplicity and good performance with prefetching.
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Denormalized count for performance
    like_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['created_at']  # Chronological order within each level
        indexes = [
            models.Index(fields=['post', 'parent']),  # For efficient tree queries
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['author']),
        ]
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.id}"
    
    @property
    def depth(self):
        """Calculate comment depth for display purposes"""
        depth = 0
        parent = self.parent
        while parent:
            depth += 1
            parent = parent.parent
        return depth


class Like(models.Model):
    """
    Polymorphic likes for both posts and comments.
    Uses database constraints to prevent duplicate likes.
    """
    CONTENT_TYPE_CHOICES = [
        ('post', 'Post'),
        ('comment', 'Comment'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES)
    object_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Prevent duplicate likes - database-level constraint
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_type', 'object_id'],
                name='unique_user_like_per_object'
            )
        ]
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),  # For karma calculations
        ]
    
    def __str__(self):
        return f"{self.user.username} likes {self.content_type} {self.object_id}"


class KarmaEvent(models.Model):
    """
    Event-based karma system. No stored totals - calculated dynamically.
    
    This approach provides:
    1. Full audit trail of karma changes
    2. Ability to recalculate karma with different rules
    3. Time-based karma queries (last 24h leaderboard)
    4. Prevents karma manipulation bugs from stored totals
    
    Karma Rules:
    - POST_LIKE: 5 points
    - COMMENT_LIKE: 1 point
    """
    EVENT_TYPES = [
        ('POST_LIKE', 'Post Like'),
        ('COMMENT_LIKE', 'Comment Like'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='karma_events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    source_id = models.PositiveIntegerField()  # ID of the liked post/comment
    points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),  # For user karma queries
            models.Index(fields=['created_at']),  # For time-based queries
            models.Index(fields=['event_type', 'source_id']),  # For preventing duplicates
        ]
    
    def __str__(self):
        return f"{self.user.username} +{self.points} karma ({self.event_type})"
    
    @classmethod
    def get_user_karma_last_24h(cls, user):
        """Get user's karma from last 24 hours"""
        since = timezone.now() - timedelta(hours=24)
        return cls.objects.filter(
            user=user,
            created_at__gte=since
        ).aggregate(total=Sum('points'))['total'] or 0
    
    @classmethod
    def get_leaderboard_last_24h(cls, limit=5):
        """
        Get top users by karma in last 24 hours.
        
        This is the key optimization challenge - must be a single efficient query.
        Uses Django ORM aggregation to avoid N+1 queries.
        """
        since = timezone.now() - timedelta(hours=24)
        
        return User.objects.filter(
            karma_events__created_at__gte=since
        ).annotate(
            karma_24h=Sum('karma_events__points')
        ).order_by('-karma_24h')[:limit]


# Signal handlers for maintaining denormalized counts
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=Like)
def create_karma_event_and_update_counts(sender, instance, created, **kwargs):
    """
    When a like is created:
    1. Create corresponding karma event
    2. Update denormalized like counts
    3. Handle concurrency with select_for_update
    """
    if not created:
        return
    
    # Determine karma points and target object
    if instance.content_type == 'post':
        points = 5
        try:
            post = Post.objects.select_for_update().get(id=instance.object_id)
            post.like_count += 1
            post.save(update_fields=['like_count'])
            target_user = post.author
        except Post.DoesNotExist:
            return
    else:  # comment
        points = 1
        try:
            comment = Comment.objects.select_for_update().get(id=instance.object_id)
            comment.like_count += 1
            comment.save(update_fields=['like_count'])
            target_user = comment.author
        except Comment.DoesNotExist:
            return
    
    # Create karma event for the content author (not the liker)
    KarmaEvent.objects.create(
        user=target_user,
        event_type=f"{instance.content_type.upper()}_LIKE",
        source_id=instance.object_id,
        points=points
    )


@receiver(post_delete, sender=Like)
def remove_karma_event_and_update_counts(sender, instance, **kwargs):
    """
    When a like is deleted (unlike):
    1. Remove corresponding karma event
    2. Update denormalized like counts
    """
    # Update counts
    if instance.content_type == 'post':
        try:
            post = Post.objects.select_for_update().get(id=instance.object_id)
            post.like_count = max(0, post.like_count - 1)
            post.save(update_fields=['like_count'])
            target_user = post.author
        except Post.DoesNotExist:
            return
    else:  # comment
        try:
            comment = Comment.objects.select_for_update().get(id=instance.object_id)
            comment.like_count = max(0, comment.like_count - 1)
            comment.save(update_fields=['like_count'])
            target_user = comment.author
        except Comment.DoesNotExist:
            return
    
    # Remove karma event
    KarmaEvent.objects.filter(
        user=target_user,
        event_type=f"{instance.content_type.upper()}_LIKE",
        source_id=instance.object_id
    ).delete()


@receiver(post_save, sender=Comment)
def update_post_comment_count(sender, instance, created, **kwargs):
    """Update post comment count when new comment is created"""
    if created:
        Post.objects.filter(id=instance.post.id).update(
            comment_count=models.F('comment_count') + 1
        )


@receiver(post_delete, sender=Comment)
def decrease_post_comment_count(sender, instance, **kwargs):
    """Update post comment count when comment is deleted"""
    Post.objects.filter(id=instance.post.id).update(
        comment_count=models.F('comment_count') - 1
    )