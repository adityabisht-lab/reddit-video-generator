import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// Configure axios
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
axios.defaults.baseURL = API_BASE_URL;

// Components
const Header = ({ user, onLogout }) => (
  <header className="bg-blue-600 text-white p-4 shadow-lg">
    <div className="container mx-auto flex justify-between items-center">
      <h1 className="text-2xl font-bold">Reddit Video Generator</h1>
      {user && (
        <div className="flex items-center space-x-4">
          <span>Welcome, {user.email}</span>
          <button
            onClick={onLogout}
            className="bg-blue-800 hover:bg-blue-900 px-4 py-2 rounded transition-colors"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  </header>
);

const AuthForm = ({ onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const endpoint = isLogin ? '/api/login' : '/api/register';
      const response = await axios.post(endpoint, { email, password });
      
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      onLogin({ email });
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6 text-center">
          {isLogin ? 'Login' : 'Register'}
        </h2>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
              required
            />
          </div>
          
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:opacity-50"
          >
            {loading ? 'Processing...' : isLogin ? 'Login' : 'Register'}
          </button>
        </form>
        
        <p className="text-center mt-4">
          {isLogin ? "Don't have an account?" : "Already have an account?"}{' '}
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-blue-600 hover:text-blue-800"
          >
            {isLogin ? 'Register' : 'Login'}
          </button>
        </p>
      </div>
    </div>
  );
};

const VideoCreator = ({ onVideoCreated }) => {
  const [redditUrl, setRedditUrl] = useState('');
  const [maxComments, setMaxComments] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post('/api/create-video', {
        reddit_url: redditUrl,
        max_comments: maxComments
      });
      
      onVideoCreated(response.data.video_id);
      setRedditUrl('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create video');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md mb-8">
      <h2 className="text-xl font-bold mb-4">Create New Video</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-gray-700 text-sm font-bold mb-2">
            Reddit Post URL
          </label>
          <input
            type="url"
            value={redditUrl}
            onChange={(e) => setRedditUrl(e.target.value)}
            placeholder="https://www.reddit.com/r/example/comments/..."
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
            required
          />
        </div>
        
        <div className="mb-4">
          <label className="block text-gray-700 text-sm font-bold mb-2">
            Max Comments to Include
          </label>
          <select
            value={maxComments}
            onChange={(e) => setMaxComments(parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
          >
            <option value={3}>3 Comments</option>
            <option value={5}>5 Comments</option>
            <option value={10}>10 Comments</option>
          </select>
        </div>
        
        <button
          type="submit"
          disabled={loading}
          className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:opacity-50"
        >
          {loading ? 'Creating Video...' : 'Create Video'}
        </button>
      </form>
    </div>
  );
};

const VideoList = ({ videos, onRefresh }) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Your Videos</h2>
        <button
          onClick={onRefresh}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
        >
          Refresh
        </button>
      </div>
      
      {videos.length === 0 ? (
        <p className="text-gray-500">No videos created yet. Create your first video above!</p>
      ) : (
        <div className="space-y-4">
          {videos.map((video) => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      )}
    </div>
  );
};

const VideoCard = ({ video }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'processing': return 'text-yellow-600';
      case 'error': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'completed': return 'Ready for Download';
      case 'processing': return 'Processing...';
      case 'error': return 'Error Occurred';
      default: return 'Unknown Status';
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="font-semibold text-lg mb-2 truncate">{video.title}</h3>
          <p className={`text-sm font-medium ${getStatusColor(video.status)}`}>
            {getStatusText(video.status)}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Created: {new Date(video.created_at).toLocaleString()}
          </p>
        </div>
        
        <div className="ml-4">
          {video.status === 'error' && (
            <span className="text-red-600 text-sm font-medium">Failed</span>
          )}
        </div>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [user, setUser] = useState(null);
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing token
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      // Verify token by fetching user videos
      fetchVideos().then(() => {
        setUser({ email: 'user@example.com' }); // In real app, decode from token
      }).catch(() => {
        // Token invalid, remove it
        localStorage.removeItem('token');
        delete axios.defaults.headers.common['Authorization'];
      }).finally(() => {
        setLoading(false);
      });
    } else {
      setLoading(false);
    }
  }, []);

  const fetchVideos = async () => {
    try {
      const response = await axios.get('/api/videos');
      setVideos(response.data);
    } catch (error) {
      console.error('Failed to fetch videos:', error);
      throw error;
    }
  };

  const handleLogin = (userData) => {
    setUser(userData);
    fetchVideos();
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
    setVideos([]);
  };

  const handleVideoCreated = (videoId) => {
    // Refresh videos list
    fetchVideos();
    
    // Show success message
    alert('Video creation started! It will appear in your videos list when ready.');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!user) {
    return <AuthForm onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Header user={user} onLogout={handleLogout} />
      
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <VideoCreator onVideoCreated={handleVideoCreated} />
          <VideoList videos={videos} onRefresh={fetchVideos} />
        </div>
      </main>
      
      <footer className="bg-gray-800 text-white p-4 mt-12">
        <div className="container mx-auto text-center">
          <p>&copy; 2025 Reddit Video Generator. Built with React and FastAPI.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;status === 'completed' && video.video_url && (
            <a
              href={`${API_BASE_URL}${video.video_url}`}
              download
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm transition-colors"
            >
              Download Video
            </a>
          )}
          
          {video.status === 'processing' && (
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              <span className="text-sm text-gray-500">Processing</span>
            </div>
          )}
          
          {video.
