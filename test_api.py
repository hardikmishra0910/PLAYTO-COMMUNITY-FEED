#!/usr/bin/env python
"""
Simple script to test the Community Feed API endpoints
"""
import os
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'community_feed.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Post, Comment, Like, KarmaEvent

def test_leaderboard_api():
    """Test the leaderboard API endpoint"""
    
    # First, let's get a token by logging in
    login_url = 'http://127.0.0.1:8000/api/auth/login/'
    login_data = {
        'username': 'user1',
        'password': 'password123'
    }
    
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            token = response.json()['access']
            print("✅ Login successful")
        else:
            print(f"❌ Login failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Test leaderboard endpoint
    headers = {'Authorization': f'Bearer {token}'}
    leaderboard_url = 'http://127.0.0.1:8000/api/leaderboard/'
    
    try:
        response = requests.get(leaderboard_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("✅ Leaderboard API working")
            print(f"📊 Found {len(data)} users in leaderboard:")
            for i, user in enumerate(data, 1):
                print(f"  {i}. @{user['username']} - {user['karma_24h']} karma")
        else:
            print(f"❌ Leaderboard failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Leaderboard error: {e}")
    
    # Test posts endpoint
    posts_url = 'http://127.0.0.1:8000/api/posts/'
    try:
        response = requests.get(posts_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            posts = data.get('results', data)
            print(f"✅ Posts API working - {len(posts)} posts found")
        else:
            print(f"❌ Posts failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Posts error: {e}")

def print_database_stats():
    """Print current database statistics"""
    print("\n📈 Database Statistics:")
    print(f"Users: {User.objects.count()}")
    print(f"Posts: {Post.objects.count()}")
    print(f"Comments: {Comment.objects.count()}")
    print(f"Likes: {Like.objects.count()}")
    print(f"Karma Events: {KarmaEvent.objects.count()}")
    
    # Show leaderboard calculation
    print("\n🏆 Current Leaderboard (Last 24h):")
    leaders = KarmaEvent.get_leaderboard_last_24h(5)
    for i, user in enumerate(leaders, 1):
        print(f"  {i}. @{user.username} - {user.karma_24h} karma")

if __name__ == '__main__':
    print("🧪 Testing Community Feed API\n")
    print_database_stats()
    print("\n" + "="*50)
    test_leaderboard_api()