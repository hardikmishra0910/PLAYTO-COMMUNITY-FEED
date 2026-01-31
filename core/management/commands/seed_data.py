from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Post, Comment, Like
import random


class Command(BaseCommand):
    help = 'Seed database with test data'

    def handle(self, *args, **options):
        self.stdout.write('Creating test users...')
        
        # Create test users
        users = []
        for i in range(10):
            username = f'user{i+1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': f'User',
                    'last_name': f'{i+1}'
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            users.append(user)
        
        self.stdout.write('Creating test posts...')
        
        # Create test posts
        posts = []
        post_contents = [
            "Just discovered this amazing new Python library! Anyone else tried it?",
            "Working on a Django project and loving the ORM optimizations.",
            "React hooks have completely changed how I write components.",
            "PostgreSQL query optimization tips anyone?",
            "Building a REST API with DRF - best practices?",
            "Tailwind CSS is a game changer for rapid prototyping.",
            "Docker containers make deployment so much easier.",
            "Anyone using TypeScript with React? Thoughts?",
            "Database indexing strategies for large datasets?",
            "Code review best practices for teams?"
        ]
        
        for i, content in enumerate(post_contents):
            post = Post.objects.create(
                author=users[i % len(users)],
                content=content
            )
            posts.append(post)
        
        self.stdout.write('Creating test comments...')
        
        # Create test comments with some replies
        comment_contents = [
            "Great point! I've been using this approach too.",
            "Thanks for sharing, very helpful!",
            "I disagree, here's why...",
            "Can you elaborate on this?",
            "This is exactly what I was looking for!",
            "Have you considered this alternative?",
            "Interesting perspective, never thought of it that way.",
            "I had the same issue, here's how I solved it.",
            "This doesn't work in all cases though.",
            "Brilliant solution, thanks!"
        ]
        
        comments = []
        for post in posts:
            # Create 2-5 root comments per post
            num_comments = random.randint(2, 5)
            for i in range(num_comments):
                comment = Comment.objects.create(
                    post=post,
                    author=random.choice(users),
                    content=random.choice(comment_contents)
                )
                comments.append(comment)
                
                # 30% chance to create a reply
                if random.random() < 0.3:
                    reply = Comment.objects.create(
                        post=post,
                        parent=comment,
                        author=random.choice(users),
                        content=random.choice(comment_contents)
                    )
                    comments.append(reply)
                    
                    # 20% chance to create a reply to the reply
                    if random.random() < 0.2:
                        nested_reply = Comment.objects.create(
                            post=post,
                            parent=reply,
                            author=random.choice(users),
                            content=random.choice(comment_contents)
                        )
                        comments.append(nested_reply)
        
        self.stdout.write('Creating test likes...')
        
        # Create random likes for posts and comments
        for post in posts:
            # Each post gets 1-8 likes
            num_likes = random.randint(1, 8)
            liked_users = random.sample(users, min(num_likes, len(users)))
            for user in liked_users:
                Like.objects.get_or_create(
                    user=user,
                    content_type='post',
                    object_id=post.id
                )
        
        for comment in comments:
            # Each comment gets 0-5 likes
            num_likes = random.randint(0, 5)
            if num_likes > 0:
                liked_users = random.sample(users, min(num_likes, len(users)))
                for user in liked_users:
                    Like.objects.get_or_create(
                        user=user,
                        content_type='comment',
                        object_id=comment.id
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created:\n'
                f'- {len(users)} users\n'
                f'- {len(posts)} posts\n'
                f'- {len(comments)} comments\n'
                f'- {Like.objects.count()} likes'
            )
        )