from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Prefetch, Sum
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Post, Comment, Like, KarmaEvent
from .serializers import (
    PostSerializer, CommentSerializer, CommentCreateSerializer,
    LikeSerializer, LeaderboardSerializer, UserSerializer
)


class PostListCreateView(generics.ListCreateAPIView):
    """
    List all posts or create a new post.
    
    Optimizations:
    - select_related for author to avoid N+1 queries
    - Ordering by creation date for consistent pagination
    """
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Post.objects.select_related('author').order_by('-created_at')


class PostCommentsView(generics.RetrieveAPIView):
    """
    Get a post with its complete comment tree.
    
    This is the critical optimization challenge - loading nested comments
    without N+1 queries.
    
    Strategy:
    1. Fetch all comments for the post in a single query
    2. Build the tree structure in Python using a dictionary lookup
    3. Attach replies to parent comments as 'prefetched_replies' attribute
    4. Serialize the root comments, which recursively includes replies
    
    This approach:
    - Uses only 2 DB queries total (post + all comments)
    - Builds tree in O(n) time where n = number of comments
    - Avoids recursive DB queries that would cause N+1 problems
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        # Get the post
        post = get_object_or_404(Post.objects.select_related('author'), pk=pk)
        
        # Fetch ALL comments for this post in a single query
        # This is key to avoiding N+1 - we get everything at once
        all_comments = Comment.objects.filter(post=post).select_related('author').order_by('created_at')
        
        # Build comment tree in Python to avoid recursive queries
        comment_dict = {}
        root_comments = []
        
        # First pass: create dictionary of all comments
        for comment in all_comments:
            comment.prefetched_replies = []  # Initialize replies list
            comment_dict[comment.id] = comment
        
        # Second pass: build parent-child relationships
        for comment in all_comments:
            if comment.parent_id:
                # This is a reply - add to parent's replies
                parent = comment_dict.get(comment.parent_id)
                if parent:
                    parent.prefetched_replies.append(comment)
            else:
                # This is a root comment
                root_comments.append(comment)
        
        # Serialize post and comments
        post_data = PostSerializer(post, context={'request': request}).data
        comments_data = CommentSerializer(root_comments, many=True, context={'request': request}).data
        
        return Response({
            'post': post_data,
            'comments': comments_data
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_comment(request):
    """
    Create a new comment or reply.
    
    Handles both top-level comments (parent=null) and replies (parent=comment_id).
    """
    serializer = CommentCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        comment = serializer.save()
        # Return the created comment with full details
        response_serializer = CommentSerializer(comment, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_post(request, pk):
    """
    Like or unlike a post (toggle behavior).
    
    Concurrency safety:
    - Uses database constraints to prevent duplicate likes
    - Handles IntegrityError gracefully for race conditions
    - Uses select_for_update for atomic count updates (handled in signals)
    """
    post = get_object_or_404(Post, pk=pk)
    
    # Check if user already liked this post
    existing_like = Like.objects.filter(
        user=request.user,
        content_type='post',
        object_id=post.id
    ).first()
    
    if existing_like:
        # Unlike - delete the like
        existing_like.delete()
        return Response({
            'liked': False,
            'like_count': post.like_count  # Will be updated by signal
        })
    else:
        # Like - create new like
        try:
            with transaction.atomic():
                Like.objects.create(
                    user=request.user,
                    content_type='post',
                    object_id=post.id
                )
            # Refresh post to get updated count
            post.refresh_from_db()
            return Response({
                'liked': True,
                'like_count': post.like_count
            })
        except Exception as e:
            # Handle race condition - like might have been created by another request
            return Response({
                'liked': True,
                'like_count': post.like_count
            })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_comment(request, pk):
    """
    Like or unlike a comment (toggle behavior).
    
    Same concurrency safety approach as like_post.
    """
    comment = get_object_or_404(Comment, pk=pk)
    
    # Check if user already liked this comment
    existing_like = Like.objects.filter(
        user=request.user,
        content_type='comment',
        object_id=comment.id
    ).first()
    
    if existing_like:
        # Unlike - delete the like
        existing_like.delete()
        return Response({
            'liked': False,
            'like_count': comment.like_count
        })
    else:
        # Like - create new like
        try:
            with transaction.atomic():
                Like.objects.create(
                    user=request.user,
                    content_type='comment',
                    object_id=comment.id
                )
            # Refresh comment to get updated count
            comment.refresh_from_db()
            return Response({
                'liked': True,
                'like_count': comment.like_count
            })
        except Exception as e:
            # Handle race condition
            return Response({
                'liked': True,
                'like_count': comment.like_count
            })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leaderboard(request):
    """
    Get top 5 users by karma earned in the last 24 hours.
    
    This is the key performance challenge - must use a single efficient query.
    
    Query breakdown:
    1. Filter karma events from last 24 hours
    2. Group by user and sum points
    3. Order by total karma descending
    4. Limit to top 5
    
    The query uses Django ORM aggregation to avoid Python loops and N+1 queries.
    All computation happens in the database for optimal performance.
    """
    leaderboard_users = KarmaEvent.get_leaderboard_last_24h(limit=5)
    
    # Handle case where no users have karma in last 24h
    if not leaderboard_users:
        return Response([])
    
    serializer = LeaderboardSerializer(leaderboard_users, many=True)
    return Response(serializer.data)


# Additional utility views for debugging/admin

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_karma(request, user_id=None):
    """Get karma for a specific user (or current user if not specified)"""
    if user_id:
        user = get_object_or_404(User, pk=user_id)
    else:
        user = request.user
    
    karma_24h = KarmaEvent.get_user_karma_last_24h(user)
    total_karma = KarmaEvent.objects.filter(user=user).aggregate(
        total=Sum('points')
    )['total'] or 0
    
    return Response({
        'user': UserSerializer(user).data,
        'karma_24h': karma_24h,
        'total_karma': total_karma
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new user"""
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        # Validation
        if not username or not email or not password:
            return Response({
                'error': 'Username, email, and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(password) < 6:
            return Response({
                'error': 'Password must be at least 6 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({
                'error': 'Username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'Email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate username format
        if not username.replace('_', '').replace('-', '').isalnum():
            return Response({
                'error': 'Username can only contain letters, numbers, hyphens, and underscores'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(username) < 3:
            return Response({
                'error': 'Username must be at least 3 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'User created successfully',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Registration failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Get current user info"""
    return Response({
        'user': UserSerializer(request.user).data
    })