# 🌟 PLAYTO Community Feed

A modern, production-quality social media platform built with Django REST Framework and React. Features threaded comments, karma system, media support, and real-time leaderboards.

![Community Feed](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Django](https://img.shields.io/badge/Django-4.2.7-green)
![React](https://img.shields.io/badge/React-18.0-blue)
![Python](https://img.shields.io/badge/Python-3.8+-yellow)

## ✨ Features

### 🚀 Core Functionality
- **User Authentication**: JWT-based secure login/registration system
- **Post Creation**: Support for text, images, and videos
- **Threaded Comments**: Reddit-style infinite comment nesting
- **Like System**: Like posts and comments with concurrency safety
- **Karma System**: Event-based karma calculation (5 points for post likes, 1 for comment likes)
- **Real-time Leaderboard**: Top 5 contributors in the last 24 hours

### 🎨 Modern UI/UX
- **Glass Morphism Design**: Beautiful modern interface with blur effects
- **Responsive Layout**: Works perfectly on desktop, tablet, and mobile
- **Smooth Animations**: Fade-in, slide-up, and hover effects
- **Dark Mode Support**: Adapts to system preferences
- **Mobile-First**: Floating leaderboard button for mobile users

### ⚡ Performance & Security
- **N+1 Query Prevention**: Optimized database queries with prefetch_related
- **Concurrency Safety**: Race condition handling with database constraints
- **Event-Based Architecture**: Karma calculated from events, not stored totals
- **Media Optimization**: Proper file handling and validation
- **CORS Configuration**: Secure cross-origin resource sharing

## 🛠️ Tech Stack

### Backend
- **Django 4.2.7**: Web framework
- **Django REST Framework**: API development
- **JWT Authentication**: Secure token-based auth
- **SQLite**: Database (easily switchable to PostgreSQL)
- **Pillow**: Image processing

### Frontend
- **React 18**: UI library
- **React Router**: Client-side routing
- **Axios**: HTTP client
- **Modern CSS**: Glass morphism, gradients, animations
- **Responsive Design**: Mobile-first approach

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 14+
- npm or yarn

### Backend Setup
```bash
# Clone the repository
git clone https://github.com/hardikmishra0910/PLAYTO-COMMUNITY-FEED.git
cd PLAYTO-COMMUNITY-FEED

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start Django server
python manage.py runserver
```

### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start React development server
npm start
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://127.0.0.1:8000
- **Admin Panel**: http://127.0.0.1:8000/admin

## � Usage

### Getting Started
1. **Register**: Create a new account with username, email, and password
2. **Login**: Sign in to access the community feed
3. **Create Posts**: Share text, images, or videos
4. **Engage**: Like posts and comments, reply to discussions
5. **Compete**: Earn karma and climb the leaderboard

### Karma System
- **Post Like**: +5 karma points
- **Comment Like**: +1 karma point
- **Leaderboard**: Updates every 30 seconds
- **24-Hour Window**: Only recent activity counts

## 🏗️ Architecture

### Database Design
```
User (Django Auth)
├── Post (content, image, video, created_at)
│   ├── Comment (threaded with parent/child relationships)
│   └── PostLike (unique constraint: user + post)
├── CommentLike (unique constraint: user + comment)
└── KarmaEvent (event-based karma tracking)
```

### API Endpoints
```
Authentication:
POST /api/auth/register/     # User registration
POST /api/auth/login/        # User login
GET  /api/auth/me/           # Current user info

Posts:
GET  /api/posts/             # List posts
POST /api/posts/             # Create post
POST /api/posts/{id}/like/   # Like/unlike post
GET  /api/posts/{id}/comments/ # Get threaded comments

Comments:
POST /api/comments/          # Create comment/reply
POST /api/comments/{id}/like/ # Like/unlike comment

Leaderboard:
GET  /api/leaderboard/       # Top 5 users (24h)
```

### Frontend Structure
```
src/
├── components/
│   ├── AuthForm.js          # Login/Register form
│   ├── EnhancedLeaderboard.js # Karma leaderboard
│   └── PostDetailView.js    # Post modal with comments
├── api.js                   # API client configuration
├── App.js                   # Main application component
└── index.css               # Global styles and animations
```

## 🔧 Development

### Key Design Decisions
1. **Event-Based Karma**: Prevents race conditions and allows for complex karma rules
2. **Threaded Comments**: Adjacency list model for infinite nesting
3. **JWT Authentication**: Stateless authentication for scalability
4. **Glass Morphism UI**: Modern design trend for better UX
5. **Mobile-First**: Responsive design starting from mobile

### Performance Optimizations
- **Prefetch Related**: Eliminates N+1 queries for comments
- **Database Constraints**: Prevents duplicate likes
- **Efficient Queries**: Single query for leaderboard calculation
- **Image Optimization**: Proper media handling and validation

### Testing
```bash
# Run backend tests
python manage.py test

# Run API tests
python test_api.py
```

## 🚀 Deployment

### Production Considerations
1. **Database**: Switch to PostgreSQL for production
2. **Media Files**: Use cloud storage (AWS S3, Cloudinary)
3. **Environment Variables**: Use .env files for sensitive data
4. **HTTPS**: Enable SSL certificates
5. **Caching**: Implement Redis for session management

### Docker Support
```dockerfile
# Backend Dockerfile included
# Frontend build process optimized
# Docker Compose configuration available
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 👨‍💻 Author

**Hardik Mishra**
- GitHub: [@hardikmishra0910](https://github.com/hardikmishra0910)
- LinkedIn: [Hardik Mishra](https://linkedin.com/in/hardikmishra0910)

## 🙏 Acknowledgments

- Django REST Framework team for excellent API tools
- React team for the amazing frontend library
- Community feedback and testing

---

**Built with ❤️ for the PLAYTO community**
