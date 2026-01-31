from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Post, Comment, Like, KarmaEvent


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested representations"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class PostSerializer(serializers.ModelSerializer):
    """
    Post serializer with author details, denormalized counts, and media support.
    Includes user's like status for the authenticated user.
    """
    author = UserSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    media_type = serializers.ReadOnlyField(source='get_media_type')
    has_media = serializers.ReadOnlyField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'author', 'content', 'created_at', 'updated_at',
            'like_count', 'comment_count', 'is_liked', 
            'image', 'video', 'media_type', 'has_media'
        ]
        read_only_fields = ['like_count', 'comment_count']
    
    def get_is_liked(self, obj):
        """Check if current user has liked this post"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(
                user=request.user,
                content_type='post',
                object_id=obj.id
            ).exists()
        return False
    
    def create(self, validated_data):
        """Set author to current user"""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate(self, data):
        """Validate post data"""
        # Ensure at least content or media is provided
        if not data.get('content', '').strip() and not data.get('image') and not data.get('video'):
            raise serializers.ValidationError("Post must have either content, image, or video.")
        
        # Validate file types
        if data.get('image'):
            allowed_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if hasattr(data['image'], 'content_type') and data['image'].content_type not in allowed_image_types:
                raise serializers.ValidationError("Only JPEG, PNG, GIF, and WebP images are allowed.")
        
        if data.get('video'):
            allowed_video_types = ['video/mp4', 'video/webm', 'video/ogg']
            if hasattr(data['video'], 'content_type') and data['video'].content_type not in allowed_video_types:
                raise serializers.ValidationError("Only MP4, WebM, and OGG videos are allowed.")
        
        return data


class CommentSerializer(serializers.ModelSerializer):
    """
    Comment serializer with nested replies support.
    
    The replies field uses a nested serializer to build the comment tree.
    This works efficiently when combined with prefetch_related in the view.
    """
    author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    depth = serializers.ReadOnlyField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'author', 'content', 'created_at', 'updated_at',
            'like_count', 'is_liked', 'depth', 'replies'
        ]
    
    def get_replies(self, obj):
        """
        Recursively serialize nested replies.
        
        This works efficiently because the view prefetches all comments
        in a single query, so no additional DB hits occur here.
        """
        if hasattr(obj, 'prefetched_replies'):
            # Use prefetched replies to avoid N+1 queries
            replies = obj.prefetched_replies
        else:
            # Fallback for individual comment serialization
            replies = obj.replies.all()
        
        return CommentSerializer(replies, many=True, context=self.context).data
    
    def get_is_liked(self, obj):
        """Check if current user has liked this comment"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(
                user=request.user,
                content_type='comment',
                object_id=obj.id
            ).exists()
        return False


class CommentCreateSerializer(serializers.ModelSerializer):
    """Separate serializer for creating comments to avoid circular references"""
    
    class Meta:
        model = Comment
        fields = ['post', 'parent', 'content']
    
    def validate(self, data):
        """Ensure parent comment belongs to the same post"""
        if data.get('parent') and data.get('post'):
            if data['parent'].post != data['post']:
                raise serializers.ValidationError(
                    "Parent comment must belong to the same post"
                )
        return data
    
    def create(self, validated_data):
        """Set author to current user"""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class LikeSerializer(serializers.ModelSerializer):
    """Serializer for like operations"""
    
    class Meta:
        model = Like
        fields = ['content_type', 'object_id']
    
    def create(self, validated_data):
        """Set user to current user and handle idempotency"""
        validated_data['user'] = self.context['request'].user
        
        # Check if like already exists (idempotent operation)
        existing_like = Like.objects.filter(
            user=validated_data['user'],
            content_type=validated_data['content_type'],
            object_id=validated_data['object_id']
        ).first()
        
        if existing_like:
            return existing_like
        
        return super().create(validated_data)


class LeaderboardSerializer(serializers.ModelSerializer):
    """
    Serializer for leaderboard entries.
    
    The karma_24h field is populated by the view's annotated query.
    """
    karma_24h = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'karma_24h']