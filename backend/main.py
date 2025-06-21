from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import jwt
import bcrypt
import sqlite3
import praw
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
import json
from transformers import pipeline
import torch
from TTS.api import TTS
import moviepy.editor as mp
from moviepy.video.fx import resize
import tempfile
import uuid
import re
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reddit Video Generator", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
os.makedirs("static", exist_ok=True)
os.makedirs("videos", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "RedditVideoGenerator/1.0")

# Database setup
def init_db():
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reddit_url TEXT NOT NULL,
            title TEXT,
            video_path TEXT,
            status TEXT DEFAULT 'processing',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Pydantic models
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class RedditVideoRequest(BaseModel):
    reddit_url: str
    max_comments: int = 5

class VideoResponse(BaseModel):
    id: int
    title: str
    status: str
    video_url: Optional[str] = None
    created_at: str

# Authentication
security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Reddit API setup
def get_reddit_client():
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

# AI Models initialization
summarizer = None
tts_model = None

def init_ai_models():
    global summarizer, tts_model
    try:
        # Initialize summarization model
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        
        # Initialize TTS model
        tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
        logger.info("AI models initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AI models: {e}")

# Initialize models on startup
@app.on_event("startup")
async def startup_event():
    init_ai_models()

# Utility functions
def clean_text(text):
    """Clean text for TTS and subtitles"""
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove Reddit formatting
    text = re.sub(r'/u/\w+', '', text)
    text = re.sub(r'/r/\w+', '', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&amp;', '&', text)
    
    # Clean up extra whitespace
    text = ' '.join(text.split())
    
    return text.strip()

def create_subtitles(text, duration, words_per_minute=150):
    """Create SRT subtitles from text"""
    words = text.split()
    words_per_second = words_per_minute / 60
    
    subtitles = []
    current_time = 0
    
    for i in range(0, len(words), 8):  # 8 words per subtitle
        chunk = ' '.join(words[i:i+8])
        chunk_duration = len(words[i:i+8]) / words_per_second
        
        start_time = current_time
        end_time = current_time + chunk_duration
        
        subtitles.append({
            'start': start_time,
            'end': end_time,
            'text': chunk
        })
        
        current_time = end_time
    
    return subtitles

def seconds_to_srt_time(seconds):
    """Convert seconds to SRT time format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', ',')

def generate_srt(subtitles):
    """Generate SRT content from subtitles"""
    srt_content = ""
    for i, subtitle in enumerate(subtitles, 1):
        start_time = seconds_to_srt_time(subtitle['start'])
        end_time = seconds_to_srt_time(subtitle['end'])
        srt_content += f"{i}\n{start_time} --> {end_time}\n{subtitle['text']}\n\n"
    return srt_content

# API Routes
@app.post("/api/register")
async def register(user: UserCreate):
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    password_hash = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    
    # Insert user
    cursor.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (user.email, password_hash)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Create token
    access_token = create_access_token({"user_id": user_id})
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login")
async def login(user: UserLogin):
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (user.email,))
    user_data = cursor.fetchone()
    conn.close()
    
    if not user_data or not bcrypt.checkpw(user.password.encode('utf-8'), user_data[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"user_id": user_data[0]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/create-video")
async def create_video(request: RedditVideoRequest, user_id: int = Depends(get_current_user)):
    try:
        # Extract Reddit post ID from URL
        reddit_url = request.reddit_url
        if "reddit.com" not in reddit_url:
            raise HTTPException(status_code=400, detail="Invalid Reddit URL")
        
        # Get Reddit client
        reddit = get_reddit_client()
        
        # Extract post ID from URL
        post_id = reddit_url.split('/')[-3] if reddit_url.endswith('/') else reddit_url.split('/')[-2]
        
        # Fetch Reddit post
        submission = reddit.submission(id=post_id)
        
        # Prepare content for summarization
        content = f"Title: {submission.title}\n\n"
        if submission.selftext:
            content += f"Post: {submission.selftext}\n\n"
        
        # Get top comments
        submission.comments.replace_more(limit=0)
        top_comments = submission.comments[:request.max_comments]
        
        comments_text = "Top Comments:\n"
        for comment in top_comments:
            if hasattr(comment, 'body') and len(comment.body) > 10:
                comments_text += f"- {comment.body[:200]}...\n"
        
        full_content = content + comments_text
        
        # Summarize content
        if summarizer is None:
            raise HTTPException(status_code=500, detail="AI model not initialized")
        
        # Split content into chunks for summarization
        max_length = 1000
        chunks = [full_content[i:i+max_length] for i in range(0, len(full_content), max_length)]
        
        summaries = []
        for chunk in chunks:
            if len(chunk.strip()) > 50:  # Only summarize substantial chunks
                summary = summarizer(chunk, max_length=150, min_length=30, do_sample=False)
                summaries.append(summary[0]['summary_text'])
        
        final_summary = ' '.join(summaries)
        final_summary = clean_text(final_summary)
        
        # Create database entry
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO videos (user_id, reddit_url, title, status) VALUES (?, ?, ?, ?)",
            (user_id, reddit_url, submission.title, 'processing')
        )
        video_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Generate video asynchronously
        asyncio.create_task(generate_video_async(video_id, final_summary, submission.title))
        
        return {"video_id": video_id, "message": "Video generation started"}
        
    except Exception as e:
        logger.error(f"Error creating video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_video_async(video_id: int, text: str, title: str):
    """Generate video asynchronously"""
    try:
        # Generate TTS audio
        audio_path = f"videos/audio_{video_id}.wav"
        if tts_model:
            tts_model.tts_to_file(text=text, file_path=audio_path)
        
        # Get audio duration
        audio_clip = mp.AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # Create subtitles
        subtitles = create_subtitles(text, duration)
        
        # Create video with green screen background
        video_width, video_height = 1920, 1080
        
        # Create green screen background
        green_screen = mp.ColorClip(size=(video_width, video_height), color=(0, 255, 0), duration=duration)
        
        # Create subtitle clips
        subtitle_clips = []
        for subtitle in subtitles:
            txt_clip = mp.TextClip(
                subtitle['text'],
                fontsize=60,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=2,
                method='caption',
                size=(video_width-100, None)
            ).set_position('center').set_start(subtitle['start']).set_duration(subtitle['end'] - subtitle['start'])
            subtitle_clips.append(txt_clip)
        
        # Composite video
        final_video = mp.CompositeVideoClip([green_screen] + subtitle_clips)
        final_video = final_video.set_audio(audio_clip)
        
        # Export video
        output_path = f"videos/video_{video_id}.mp4"
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        # Update database
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE videos SET status = ?, video_path = ? WHERE id = ?",
            ('completed', output_path, video_id)
        )
        conn.commit()
        conn.close()
        
        # Cleanup
        audio_clip.close()
        final_video.close()
        
        logger.info(f"Video {video_id} generated successfully")
        
    except Exception as e:
        logger.error(f"Error generating video {video_id}: {e}")
        
        # Update database with error status
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE videos SET status = ? WHERE id = ?",
            ('error', video_id)
        )
        conn.commit()
        conn.close()

@app.get("/api/videos")
async def get_videos(user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, status, video_path, created_at FROM videos WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    videos = cursor.fetchall()
    conn.close()
    
    video_list = []
    for video in videos:
        video_data = {
            "id": video[0],
            "title": video[1],
            "status": video[2],
            "created_at": video[4]
        }
        if video[3] and video[2] == 'completed':
            video_data["video_url"] = f"/videos/{os.path.basename(video[3])}"
        video_list.append(video_data)
    
    return video_list

@app.get("/api/video/{video_id}")
async def get_video(video_id: int, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, status, video_path, created_at FROM videos WHERE id = ? AND user_id = ?",
        (video_id, user_id)
    )
    video = cursor.fetchone()
    conn.close()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_data = {
        "id": video[0],
        "title": video[1],
        "status": video[2],
        "created_at": video[4]
    }
    
    if video[3] and video[2] == 'completed':
        video_data["video_url"] = f"/videos/{os.path.basename(video[3])}"
    
    return video_data

@app.get("/")
async def root():
    return {"message": "Reddit Video Generator API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
