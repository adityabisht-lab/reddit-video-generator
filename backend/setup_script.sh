#!/bin/bash

# Reddit Video Generator Setup Script
# This script helps you set up the development environment

echo "🚀 Setting up Reddit Video Generator..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ and try again."
    exit 1
fi

# Create project directory structure
echo "📁 Creating project structure..."
mkdir -p reddit-video-generator/{backend,frontend}
cd reddit-video-generator

# Setup backend
echo "🔧 Setting up backend..."
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p videos static

# Copy environment file
cp .env.example .env

echo "✅ Backend setup complete!"

# Setup frontend
echo "🔧 Setting up frontend..."
cd ../frontend

# Install Node.js dependencies
npm install

# Copy environment file
cp .env.example .env

echo "✅ Frontend setup complete!"

# Setup instructions
echo "
🎉 Setup complete! Next steps:

1. Configure Reddit API:
   - Go to https://www.reddit.com/prefs/apps
   - Create a new app (script type)
   - Copy Client ID and Client Secret to backend/.env

2. Start the backend:
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload

3. Start the frontend (in a new terminal):
   cd frontend
   npm run dev

4. Open http://localhost:3000 in your browser

📚 For detailed instructions, see the README.md file.
"