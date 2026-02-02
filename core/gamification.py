# Gamification System

"""
Gamification Features to Add:

1. Achievement System
   - First Post, First Comment, First Like
   - Karma milestones (100, 500, 1000, 5000)
   - Engagement achievements (10 comments in a day)
   - Social achievements (10 followers, 100 likes received)

2. Badges & Ranks
   - Contributor badges
   - Expert badges for specific topics
   - Moderator badges
   - Special event badges

3. Streaks & Challenges
   - Daily login streaks
   - Weekly posting challenges
   - Monthly karma goals
   - Community challenges

4. Leaderboards
   - All-time karma leaders
   - Monthly top contributors
   - Most helpful commenters
   - Rising stars (new users with high engagement)
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Achievement(models.Model):
    ACHIEVEMENT_TYPES = [
        ('first_post', 'First Post'),
        ('first_comment', 'First Comment'),
        ('first_like', 'First Like'),
        ('karma_100', '100 Karma Points'),
        ('karma_500', '500 Karma Points'),
        ('karma_1000', '1000 Karma Points'),
        ('karma_5000', '5000 Karma Points'),
        ('social_butterfly', '10 Comments in One Day'),
        ('popular_post', 'Post with 50+ Likes'),
        ('helpful_commenter', '100 Comment Likes'),
        ('early_adopter', 'Joined in First Month'),
        ('consistent_contributor', '30-Day Login Streak'),
    ]
    
    name = models.CharField(max_length=50, choices=ACHIEVEMENT_TYPES, unique=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=10)  # Emoji or icon class
    points = models.PositiveIntegerField(default=0)
    is_hidden = models.BooleanField(default=False)  # Hidden until unlocked
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'achievement']
    
    def __str__(self):
        return f"{self.user.username} - {self.achievement.title}"

class Badge(models.Model):
    BADGE_TYPES = [
        ('contributor', 'Contributor'),
        ('expert', 'Expert'),
        ('moderator', 'Moderator'),
        ('special', 'Special Event'),
        ('rank', 'Rank Badge'),
    ]
    
    name = models.CharField(max_length=100)
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES)
    description = models.TextField()
    icon = models.CharField(max_length=10)
    color = models.CharField(max_length=7, default='#667eea')  # Hex color
    requirements = models.TextField()  # JSON string with requirements
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    is_displayed = models.BooleanField(default=True)  # User can choose to display or hide
    
    class Meta:
        unique_together = ['user', 'badge']
    
    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"

class UserStreak(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='streak')
    current_login_streak = models.PositiveIntegerField(default=0)
    longest_login_streak = models.PositiveIntegerField(default=0)
    current_post_streak = models.PositiveIntegerField(default=0)
    longest_post_streak = models.PositiveIntegerField(default=0)
    last_login_date = models.DateField(null=True, blank=True)
    last_post_date = models.DateField(null=True, blank=True)
    
    def update_login_streak(self):
        """Update login streak when user logs in"""
        today = timezone.now().date()
        
        if self.last_login_date is None:
            # First login
            self.current_login_streak = 1
            self.longest_login_streak = 1
        elif self.last_login_date == today:
            # Already logged in today, no change
            return
        elif self.last_login_date == today - timezone.timedelta(days=1):
            # Consecutive day login
            self.current_login_streak += 1
            self.longest_login_streak = max(self.longest_login_streak, self.current_login_streak)
        else:
            # Streak broken
            self.current_login_streak = 1
        
        self.last_login_date = today
        self.save()
    
    def update_post_streak(self):
        """Update post streak when user creates a post"""
        today = timezone.now().date()
        
        if self.last_post_date is None:
            # First post
            self.current_post_streak = 1
            self.longest_post_streak = 1
        elif self.last_post_date == today:
            # Already posted today, no change
            return
        elif self.last_post_date == today - timezone.timedelta(days=1):
            # Consecutive day post
            self.current_post_streak += 1
            self.longest_post_streak = max(self.longest_post_streak, self.current_post_streak)
        else:
            # Streak broken
            self.current_post_streak = 1
        
        self.last_post_date = today
        self.save()

class Challenge(models.Model):
    CHALLENGE_TYPES = [
        ('daily', 'Daily Challenge'),
        ('weekly', 'Weekly Challenge'),
        ('monthly', 'Monthly Challenge'),
        ('special', 'Special Event'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    challenge_type = models.CharField(max_length=20, choices=CHALLENGE_TYPES)
    target_value = models.PositiveIntegerField()  # Target number to achieve
    reward_points = models.PositiveIntegerField(default=0)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title

class UserChallenge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenges')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    current_progress = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'challenge']
    
    def update_progress(self, increment=1):
        """Update challenge progress"""
        self.current_progress += increment
        
        if self.current_progress >= self.challenge.target_value and not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            
            # Award points to user (implement karma system integration)
            # KarmaEvent.objects.create(
            #     user=self.user,
            #     event_type='CHALLENGE_COMPLETED',
            #     source_id=self.challenge.id,
            #     points=self.challenge.reward_points
            # )
        
        self.save()
    
    @property
    def progress_percentage(self):
        """Calculate completion percentage"""
        if self.challenge.target_value == 0:
            return 0
        return min(100, (self.current_progress / self.challenge.target_value) * 100)

# Achievement checking functions
def check_and_award_achievements(user, event_type, **kwargs):
    """Check if user has earned any new achievements"""
    
    if event_type == 'first_post':
        achievement, created = Achievement.objects.get_or_create(
            name='first_post',
            defaults={
                'title': 'First Post!',
                'description': 'Created your first post in the community',
                'icon': '📝',
                'points': 10
            }
        )
        UserAchievement.objects.get_or_create(user=user, achievement=achievement)
    
    elif event_type == 'karma_milestone':
        karma = kwargs.get('karma', 0)
        milestones = [(100, 'karma_100'), (500, 'karma_500'), (1000, 'karma_1000'), (5000, 'karma_5000')]
        
        for threshold, achievement_name in milestones:
            if karma >= threshold:
                achievement, created = Achievement.objects.get_or_create(
                    name=achievement_name,
                    defaults={
                        'title': f'{threshold} Karma Points!',
                        'description': f'Reached {threshold} karma points',
                        'icon': '⭐',
                        'points': threshold // 10
                    }
                )
                UserAchievement.objects.get_or_create(user=user, achievement=achievement)
    
    # Add more achievement checks as needed...