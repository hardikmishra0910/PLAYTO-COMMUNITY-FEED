from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from .models import Post, Comment, Like, KarmaEvent


class LeaderboardTestCase(TestCase):
    """
    Test case for leaderboard calculation logic.
    
    This tests the key requirement: efficient single-query leaderboard
    calculation for top 5 users by karma in last 24 hours.
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test users
        self.users = []
        for i in range(7):
            user = User.objects.create_user(
                username=f'testuser{i}',
                password='testpass123'
            )
            self.users.append(user)
        
        # Create test posts
        self.posts = []
        for i, user in enumerate(self.users[:3]):
            post = Post.objects.create(
                author=user,
                content=f'Test post {i} by {user.username}'
            )
            self.posts.append(post)
        
        # Create test comments
        self.comments = []
        for i, user in enumerate(self.users[3:6]):
            comment = Comment.objects.create(
                post=self.posts[0],
                author=user,
                content=f'Test comment {i} by {user.username}'
            )
            self.comments.append(comment)
    
    def test_leaderboard_calculation_accuracy(self):
        """Test that leaderboard calculates karma correctly"""
        
        # User 0: Gets 2 post likes (2 * 5 = 10 karma)
        Like.objects.create(user=self.users[1], content_type='post', object_id=self.posts[0].id)
        Like.objects.create(user=self.users[2], content_type='post', object_id=self.posts[0].id)
        
        # User 3: Gets 3 comment likes (3 * 1 = 3 karma)  
        Like.objects.create(user=self.users[0], content_type='comment', object_id=self.comments[0].id)
        Like.objects.create(user=self.users[1], content_type='comment', object_id=self.comments[0].id)
        Like.objects.create(user=self.users[2], content_type='comment', object_id=self.comments[0].id)
        
        # User 1: Gets 1 post like (1 * 5 = 5 karma)
        Like.objects.create(user=self.users[0], content_type='post', object_id=self.posts[1].id)
        
        # User 4: Gets 1 comment like (1 * 1 = 1 karma)
        Like.objects.create(user=self.users[0], content_type='comment', object_id=self.comments[1].id)
        
        # Get leaderboard
        leaderboard = KarmaEvent.get_leaderboard_last_24h(5)
        
        # Convert to list for easier testing
        leaderboard_data = [(user.username, user.karma_24h) for user in leaderboard]
        
        # Verify correct ordering and karma calculation
        expected = [
            ('testuser0', 10),  # 2 post likes
            ('testuser1', 5),   # 1 post like
            ('testuser3', 3),   # 3 comment likes
            ('testuser4', 1),   # 1 comment like
        ]
        
        self.assertEqual(leaderboard_data, expected)
    
    def test_leaderboard_time_filtering(self):
        """Test that leaderboard only includes last 24 hours"""
        
        # Create old karma event (25 hours ago)
        old_time = timezone.now() - timedelta(hours=25)
        old_event = KarmaEvent.objects.create(
            user=self.users[0],
            event_type='POST_LIKE',
            source_id=self.posts[0].id,
            points=5
        )
        old_event.created_at = old_time
        old_event.save()
        
        # Create recent karma event (1 hour ago)
        Like.objects.create(user=self.users[1], content_type='post', object_id=self.posts[0].id)
        
        # Get leaderboard
        leaderboard = KarmaEvent.get_leaderboard_last_24h(5)
        
        # Should only include recent karma (user0 with 5 points)
        self.assertEqual(len(leaderboard), 1)
        self.assertEqual(leaderboard[0].username, 'testuser0')
        self.assertEqual(leaderboard[0].karma_24h, 5)
    
    def test_leaderboard_api_endpoint(self):
        """Test the leaderboard API endpoint"""
        
        # Authenticate
        self.client.force_authenticate(user=self.users[0])
        
        # Create some karma events
        Like.objects.create(user=self.users[1], content_type='post', object_id=self.posts[0].id)
        Like.objects.create(user=self.users[2], content_type='comment', object_id=self.comments[0].id)
        
        # Call API
        url = reverse('leaderboard')
        response = self.client.get(url)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return list of users with karma_24h field
        self.assertIsInstance(data, list)
        if data:  # If there are users in leaderboard
            self.assertIn('karma_24h', data[0])
            self.assertIn('username', data[0])
    
    def test_leaderboard_query_efficiency(self):
        """Test that leaderboard uses single query"""
        
        # Create karma events
        for i in range(10):
            Like.objects.create(
                user=self.users[i % len(self.users)], 
                content_type='post', 
                object_id=self.posts[0].id
            )
        
        # Test query count
        with self.assertNumQueries(1):
            leaderboard = list(KarmaEvent.get_leaderboard_last_24h(5))
    
    def test_concurrent_like_operations(self):
        """Test that concurrent likes don't create duplicate karma events"""
        
        # This would be more comprehensive with actual threading,
        # but we can test the constraint logic
        
        # Try to create duplicate like (should be prevented by constraint)
        Like.objects.create(user=self.users[0], content_type='post', object_id=self.posts[0].id)
        
        # Attempting duplicate should raise IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Like.objects.create(user=self.users[0], content_type='post', object_id=self.posts[0].id)
        
        # Should only have one karma event
        karma_events = KarmaEvent.objects.filter(user=self.posts[0].author)
        self.assertEqual(karma_events.count(), 1)


class CommentTreeTestCase(TestCase):
    """Test threaded comments N+1 prevention"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.post = Post.objects.create(author=self.user, content='Test post')
    
    def test_comment_tree_query_efficiency(self):
        """Test that loading comment tree doesn't cause N+1 queries"""
        
        # Create nested comment structure
        root1 = Comment.objects.create(post=self.post, author=self.user, content='Root 1')
        root2 = Comment.objects.create(post=self.post, author=self.user, content='Root 2')
        
        reply1 = Comment.objects.create(post=self.post, author=self.user, parent=root1, content='Reply 1')
        reply2 = Comment.objects.create(post=self.post, author=self.user, parent=root1, content='Reply 2')
        
        nested_reply = Comment.objects.create(post=self.post, author=self.user, parent=reply1, content='Nested')
        
        # Test API endpoint query count
        url = reverse('post-comments', kwargs={'pk': self.post.id})
        
        # Should use only 2 queries: 1 for post, 1 for all comments
        with self.assertNumQueries(2):
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify nested structure is preserved
        comments = data['comments']
        self.assertEqual(len(comments), 2)  # 2 root comments
        
        # Find root1 and verify it has replies
        root1_data = next(c for c in comments if c['content'] == 'Root 1')
        self.assertEqual(len(root1_data['replies']), 2)
        
        # Verify nested reply structure
        reply1_data = next(r for r in root1_data['replies'] if r['content'] == 'Reply 1')
        self.assertEqual(len(reply1_data['replies']), 1)
        self.assertEqual(reply1_data['replies'][0]['content'], 'Nested')