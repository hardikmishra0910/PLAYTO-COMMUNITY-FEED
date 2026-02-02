# User Profile Enhancement Ideas

"""
Advanced User Profile Features to Add:

1. User Profile Pages
   - View user's posts and comments
   - User statistics (total karma, posts, comments)
   - Join date and activity metrics

2. User Settings
   - Profile picture upload
   - Bio/description field
   - Email notification preferences
   - Privacy settings

3. Follow System
   - Follow/unfollow users
   - Following/followers count
   - Feed filtering by followed users

4. User Badges
   - Achievement system
   - Special badges for milestones
   - Karma-based ranks
"""

# Example Profile Model Extension
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"