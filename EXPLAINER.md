# Community Feed - Technical Implementation Explainer

## 🧩 Threaded Comments Implementation

### Approach: Adjacency List Pattern

I chose the **adjacency list** approach for threaded comments over alternatives like django-mptt or nested sets for the following reasons:

**Why Adjacency List:**
- **Simplicity**: Each comment stores only its `parent_id`, making the schema straightforward
- **Insertion Performance**: Adding new comments/replies is O(1) - just insert with parent reference
- **Flexibility**: Easy to move comments or change parent relationships
- **Query Optimization**: Works well with Django's `prefetch_related` for efficient tree loading

**Alternative Approaches Considered:**
- **django-mptt**: More complex, better for frequent tree operations, adds overhead
- **Materialized Path**: Good for deep trees, requires more storage and complex updates
- **Nested Sets**: Excellent for read-heavy workloads, but complex updates and poor concurrency

### Database Schema

```python
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    # ... other fields
```

**Key Indexes:**
- `(post, parent)` - For efficient tree queries
- `(post, created_at)` - For chronological ordering
- `(author)` - For user's comments

## 🚀 N+1 Query Prevention

### The Problem
Loading a post with nested comments could easily cause N+1 queries:
1. Query to get the post
2. Query to get root comments  
3. Query for each comment's replies (N queries)
4. Query for each reply's replies (N² queries)

### The Solution: Single Query + Python Tree Building

```python
def get(self, request, pk):
    # 1. Get the post (1 query)
    post = get_object_or_404(Post.objects.select_related('author'), pk=pk)
    
    # 2. Get ALL comments for this post in ONE query
    all_comments = Comment.objects.filter(post=post).select_related('author').order_by('created_at')
    
    # 3. Build tree structure in Python (O(n) time)
    comment_dict = {}
    root_comments = []
    
    # First pass: create dictionary lookup
    for comment in all_comments:
        comment.prefetched_replies = []
        comment_dict[comment.id] = comment
    
    # Second pass: build parent-child relationships
    for comment in all_comments:
        if comment.parent_id:
            parent = comment_dict.get(comment.parent_id)
            if parent:
                parent.prefetched_replies.append(comment)
        else:
            root_comments.append(comment)
```

**Result**: Only 2 database queries total, regardless of comment tree depth or size.

**Serializer Optimization:**
```python
def get_replies(self, obj):
    # Uses prefetched_replies to avoid additional queries
    if hasattr(obj, 'prefetched_replies'):
        replies = obj.prefetched_replies
    else:
        replies = obj.replies.all()  # Fallback
    
    return CommentSerializer(replies, many=True, context=self.context).data
```

## 📊 Leaderboard Query Optimization

### The Challenge
Calculate top 5 users by karma earned in the last 24 hours using a **single efficient query**.

### The Solution: Django ORM Aggregation

```python
@classmethod
def get_leaderboard_last_24h(cls, limit=5):
    since = timezone.now() - timedelta(hours=24)
    
    return User.objects.filter(
        karma_events__created_at__gte=since
    ).annotate(
        karma_24h=Sum('karma_events__points')
    ).order_by('-karma_24h')[:limit]
```

**Query Breakdown:**
1. **Filter**: Only karma events from last 24 hours
2. **Group By**: Implicitly groups by user (due to annotation)
3. **Aggregate**: Sums karma points per user
4. **Order**: Descends by total karma
5. **Limit**: Top 5 results

**Generated SQL** (approximately):
```sql
SELECT users.*, SUM(karma_events.points) as karma_24h
FROM auth_user users
JOIN core_karmaevent karma_events ON users.id = karma_events.user_id
WHERE karma_events.created_at >= %s
GROUP BY users.id
ORDER BY karma_24h DESC
LIMIT 5;
```

**Performance**: Single query, database-level aggregation, no Python loops.

## 🔒 Concurrency Safety Implementation

### Like System Race Conditions

**Problem**: Two users liking the same post simultaneously could cause:
- Duplicate likes in database
- Incorrect like counts
- Lost karma events

**Solution**: Database Constraints + Atomic Operations

```python
class Like(models.Model):
    # ... fields ...
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_type', 'object_id'],
                name='unique_user_like_per_object'
            )
        ]
```

**Signal Handler with select_for_update:**
```python
@receiver(post_save, sender=Like)
def create_karma_event_and_update_counts(sender, instance, created, **kwargs):
    if not created:
        return
    
    if instance.content_type == 'post':
        # Lock the post row for atomic count update
        post = Post.objects.select_for_update().get(id=instance.object_id)
        post.like_count += 1
        post.save(update_fields=['like_count'])
```

**Race Condition Handling:**
```python
try:
    with transaction.atomic():
        Like.objects.create(user=request.user, content_type='post', object_id=post.id)
except IntegrityError:
    # Like already exists - handle gracefully
    return Response({'liked': True, 'like_count': post.like_count})
```

## 💾 Karma System Architecture

### Event-Based Design (No Stored Totals)

**Why Event-Based:**
- **Audit Trail**: Complete history of karma changes
- **Recalculation**: Can change karma rules and recalculate
- **Time-Based Queries**: Easy to get karma for specific periods
- **Data Integrity**: No risk of karma total corruption

**Schema:**
```python
class KarmaEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    source_id = models.PositiveIntegerField()  # ID of liked post/comment
    points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
```

**Karma Rules:**
- Post like = 5 karma points
- Comment like = 1 karma point
- Points awarded to content author (not the liker)

## 🐛 Common AI Bug and Fix

### Bug: N+1 Queries in Comment Serialization

**What AI Might Generate:**
```python
# BAD: This causes N+1 queries
class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    
    def get_replies(self, obj):
        # This hits the database for each comment!
        replies = obj.replies.all()
        return CommentSerializer(replies, many=True).data
```

**The Problem:**
- For each comment, `obj.replies.all()` executes a new query
- With nested comments, this becomes exponentially worse
- 100 comments = 100+ database queries

**The Fix:**
```python
# GOOD: Uses prefetched data
def get_replies(self, obj):
    if hasattr(obj, 'prefetched_replies'):
        # Use data from our optimized view
        replies = obj.prefetched_replies
    else:
        # Fallback for individual serialization
        replies = obj.replies.all()
    
    return CommentSerializer(replies, many=True, context=self.context).data
```

**Why This Works:**
- View prefetches all comments in single query
- Builds tree structure in Python
- Serializer uses prefetched data instead of hitting database
- Result: 2 queries total instead of N+1

## 🏗 Database Indexes Strategy

**Critical Indexes Added:**

1. **Posts**: `(-created_at)` for feed ordering
2. **Comments**: `(post, parent)` for tree queries  
3. **Likes**: `(content_type, object_id)` for like lookups
4. **KarmaEvents**: `(user, created_at)` for leaderboard queries
5. **KarmaEvents**: `(created_at)` for time-based filtering

These indexes ensure all major queries run efficiently even with large datasets.

## 🚀 Performance Characteristics

**Feed Loading**: O(1) queries (paginated posts + authors)
**Comment Tree**: O(1) queries (single comment fetch + Python tree building)  
**Leaderboard**: O(1) query (database aggregation)
**Like Operations**: O(1) with proper locking
**Karma Calculation**: O(1) with indexed time queries

This architecture scales efficiently to thousands of posts and comments while maintaining sub-second response times.