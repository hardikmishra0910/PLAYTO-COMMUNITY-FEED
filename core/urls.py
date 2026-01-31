from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('auth/register/', views.register_user, name='register'),
    path('auth/me/', views.current_user, name='current-user'),
    
    # Posts
    path('posts/', views.PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<int:pk>/comments/', views.PostCommentsView.as_view(), name='post-comments'),
    path('posts/<int:pk>/like/', views.like_post, name='like-post'),
    
    # Comments
    path('comments/', views.create_comment, name='create-comment'),
    path('comments/<int:pk>/like/', views.like_comment, name='like-comment'),
    
    # Leaderboard
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    
    # Utility
    path('users/<int:user_id>/karma/', views.user_karma, name='user-karma'),
    path('users/me/karma/', views.user_karma, name='my-karma'),
]