# 🚀 Deployment Guide

This guide explains how to deploy the PLAYTO Community Feed application using Render (backend) and Vercel (frontend).

## 🏗️ Architecture

- **Backend**: Django REST API deployed on Render with PostgreSQL
- **Frontend**: React SPA deployed on Vercel
- **Database**: PostgreSQL on Render
- **Media**: Static files served via WhiteNoise

## 🔧 Backend Deployment (Render)

### 1. Create Render Account
- Go to [render.com](https://render.com) and sign up
- Connect your GitHub account

### 2. Create PostgreSQL Database
1. Click "New" → "PostgreSQL"
2. Name: `playto-community-feed-db`
3. Database Name: `playto_community_feed`
4. User: `playto_user`
5. Region: Choose closest to your users
6. Plan: Free tier
7. Click "Create Database"

### 3. Deploy Backend Service
1. Click "New" → "Web Service"
2. Connect your GitHub repository: `hardikmishra0910/PLAYTO-COMMUNITY-FEED`
3. Configure:
   - **Name**: `playto-community-feed-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command**: `gunicorn community_feed.wsgi:application`

### 4. Environment Variables
Add these environment variables in Render dashboard:

```
SECRET_KEY=your-secret-key-here
DEBUG=False
DATABASE_URL=postgresql://playto_user:password@hostname:port/playto_community_feed
ALLOWED_HOSTS=playto-community-feed-backend.onrender.com,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=https://playto-community-feed.vercel.app,http://localhost:3000
```

### 5. Deploy
- Click "Create Web Service"
- Wait for deployment to complete
- Your backend will be available at: `https://playto-community-feed-backend.onrender.com`

## 🌐 Frontend Deployment (Vercel)

### 1. Create Vercel Account
- Go to [vercel.com](https://vercel.com) and sign up
- Connect your GitHub account

### 2. Import Project
1. Click "New Project"
2. Import `hardikmishra0910/PLAYTO-COMMUNITY-FEED`
3. Configure:
   - **Framework Preset**: Create React App
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`

### 3. Environment Variables
Add in Vercel dashboard:

```
REACT_APP_API_URL=https://playto-community-feed-backend.onrender.com
```

### 4. Deploy
- Click "Deploy"
- Your frontend will be available at: `https://playto-community-feed.vercel.app`

## 🔄 Automatic Deployments

Both services are configured for automatic deployments:
- **Render**: Deploys on every push to `main` branch
- **Vercel**: Deploys on every push to `main` branch

## 🧪 Testing Deployment

1. Visit your frontend URL
2. Register a new account
3. Create a post with image/video
4. Test commenting and liking
5. Check leaderboard functionality

## 🔧 Troubleshooting

### Backend Issues
- Check Render logs for Python/Django errors
- Verify environment variables are set correctly
- Ensure database connection is working

### Frontend Issues
- Check Vercel function logs
- Verify API URL is correct
- Test CORS configuration

### Database Issues
- Check PostgreSQL connection
- Run migrations manually if needed
- Verify database credentials

## 📊 Monitoring

### Render
- View logs in Render dashboard
- Monitor resource usage
- Set up alerts for downtime

### Vercel
- View function logs
- Monitor performance metrics
- Check deployment status

## 🔒 Security Considerations

1. **Environment Variables**: Never commit secrets to Git
2. **HTTPS**: Both services use HTTPS by default
3. **CORS**: Properly configured for production domains
4. **Database**: PostgreSQL with proper authentication
5. **Static Files**: Served securely via WhiteNoise

## 💰 Cost Estimation

### Free Tier Limits
- **Render**: 750 hours/month, 512MB RAM
- **Vercel**: 100GB bandwidth, 6000 serverless function executions
- **PostgreSQL**: 1GB storage, 97 connection hours

### Scaling Options
- **Render**: Upgrade to paid plans for more resources
- **Vercel**: Pro plan for more bandwidth and features
- **Database**: Upgrade for more storage and connections

## 🚀 Performance Optimization

1. **Static Files**: Compressed and cached via WhiteNoise
2. **Database**: Indexed queries for better performance
3. **Frontend**: Optimized React build with code splitting
4. **CDN**: Vercel's global CDN for fast content delivery

## 📈 Next Steps

1. Set up monitoring and alerts
2. Configure custom domain names
3. Implement CI/CD pipelines
4. Add error tracking (Sentry)
5. Set up backup strategies