# Reddit API Configuration
# Get these from https://www.reddit.com/prefs/apps
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=RedditVideoGenerator/1.0

# JWT Secret Key (generate a secure random string)
SECRET_KEY=your_very_secure_secret_key_change_this_in_production

# Database URL (SQLite by default)
DATABASE_URL=sqlite:///./app.db

# Environment
ENVIRONMENT=development

# CORS Origins (for production, set to your frontend domain)
CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]