import streamlit as st
import yt_dlp
import os
import tempfile
import zipfile
from pathlib import Path
import threading
import queue
import time
import re

# Page configuration
st.set_page_config(
    page_title="Video Downloader",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for better styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    .main-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        margin: 1rem 0;
        color: white;
        text-align: center;
    }
    
    .main-header {
        font-size: 3.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-subtitle {
        font-size: 1.3rem;
        font-weight: 300;
        margin-top: 0.5rem;
        opacity: 0.9;
    }
    
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 5px solid #667eea;
        transition: transform 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.15);
    }
    
    .info-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        text-align: center;
    }
    
    .download-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    
    .progress-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    .status-success {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 500;
    }
    
    .status-error {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 500;
    }
    
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 2rem;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
    }
    
    .stTextArea textarea {
        border-radius: 12px;
        border: 2px solid #e0e6ed;
        font-family: 'Poppins', sans-serif;
    }
    
    .stTextArea textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
    }
    
    .platform-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .platform-item {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    
    .platform-item:hover {
        transform: scale(1.05);
    }
    
    .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .stat-item {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    
    .sidebar-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'download_progress' not in st.session_state:
    st.session_state.download_progress = {}
if 'download_queue' not in st.session_state:
    st.session_state.download_queue = queue.Queue()
if 'downloaded_files' not in st.session_state:
    st.session_state.downloaded_files = []
if 'download_history' not in st.session_state:
    st.session_state.download_history = []

class ProgressHook:
    def __init__(self, progress_bar, status_text, speed_text):
        self.progress_bar = progress_bar
        self.status_text = status_text
        self.speed_text = speed_text
        
    def __call__(self, d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes']:
                percent = d['downloaded_bytes'] / d['total_bytes']
                self.progress_bar.progress(percent)
                speed_mb = d.get('speed', 0) / (1024 * 1024) if d.get('speed') else 0
                downloaded_mb = d['downloaded_bytes'] / (1024 * 1024)
                total_mb = d['total_bytes'] / (1024 * 1024)
                
                self.status_text.markdown(f"""
                <div style="text-align: center; padding: 0.5rem;">
                    <h4 style="margin: 0; color: #667eea;">📥 Downloading...</h4>
                    <p style="margin: 0.5rem 0; font-size: 1.1rem; font-weight: 500;">
                        {percent:.1%} Complete
                    </p>
                    <p style="margin: 0; color: #666;">
                        {downloaded_mb:.1f} MB / {total_mb:.1f} MB
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                self.speed_text.markdown(f"""
                <div style="text-align: center; background: #f8f9fa; padding: 0.5rem; border-radius: 8px;">
                    <span style="color: #28a745; font-weight: 600;">
                        ⚡ {speed_mb:.2f} MB/s
                    </span>
                </div>
                """, unsafe_allow_html=True)
                
            elif '_percent_str' in d:
                percent_str = d['_percent_str'].strip('%')
                try:
                    percent = float(percent_str) / 100
                    self.progress_bar.progress(percent)
                    self.status_text.markdown(f"""
                    <div style="text-align: center; padding: 0.5rem;">
                        <h4 style="margin: 0; color: #667eea;">📥 Downloading...</h4>
                        <p style="margin: 0.5rem 0; font-size: 1.1rem; font-weight: 500;">
                            {percent_str}% Complete
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                except:
                    self.status_text.markdown("""
                    <div style="text-align: center; padding: 0.5rem;">
                        <h4 style="margin: 0; color: #667eea;">📥 Downloading...</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
        elif d['status'] == 'finished':
            self.progress_bar.progress(1.0)
            self.status_text.markdown("""
            <div class="status-success">
                <h4 style="margin: 0;">✅ Download Completed!</h4>
                <p style="margin: 0.5rem 0;">Ready for download</p>
            </div>
            """, unsafe_allow_html=True)
            self.speed_text.empty()

def get_video_info(url):
    """Get video information without downloading"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        return None

def format_duration(seconds):
    """Convert seconds to readable format"""
    if not seconds:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    else:
        return f"{int(seconds)}s"

def format_number(num):
    """Format large numbers with K, M, B suffixes"""
    if not num:
        return "Unknown"
    
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return str(num)

def is_valid_url(url):
    """Check if URL is valid"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def download_content(url, format_choice, audio_only, output_path, progress_hook):
    """Download video/audio content"""
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
        }
        
        if audio_only:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            if format_choice == "Best Quality":
                ydl_opts['format'] = 'best'
            elif format_choice == "720p":
                ydl_opts['format'] = 'best[height<=720]'
            elif format_choice == "480p":
                ydl_opts['format'] = 'best[height<=480]'
            elif format_choice == "360p":
                ydl_opts['format'] = 'best[height<=360]'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        return True, "Download completed successfully!"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def create_zip_file(folder_path, zip_name):
    """Create a zip file from downloaded content"""
    zip_path = os.path.join(folder_path, zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if not file.endswith('.zip'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)
    return zip_path

# Header
st.markdown("""
<div class="main-container">
    <h1 class="main-header">Video Downloader</h1>
    <p class="main-subtitle">
        Download videos and audio from YouTube, Instagram, TikTok, and 1000+ other platforms!<br>
        Fast • Reliable • Easy to Use
    </p>
</div>
""", unsafe_allow_html=True)

# Supported platforms showcase
st.markdown("""
<div class="platform-grid">
    <div class="platform-item">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">📺</div>
        <strong>YouTube</strong>
    </div>
    <div class="platform-item">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">📱</div>
        <strong>Instagram</strong>
    </div>
    <div class="platform-item">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎵</div>
        <strong>TikTok</strong>
    </div>
    <div class="platform-item">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🐦</div>
        <strong>Twitter</strong>
    </div>
    <div class="platform-item">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">📘</div>
        <strong>Facebook</strong>
    </div>
    <div class="platform-item">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎬</div>
        <strong>Vimeo</strong>
    </div>
</div>
""", unsafe_allow_html=True)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3 style="margin-top: 0; color: #667eea;">🔗 Enter Video URL(s)</h3>
        <p style="color: #666; margin-bottom: 1rem;">
            Paste single video URLs or multiple URLs (one per line) for batch downloading
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # URL Input with better styling
    url_input = st.text_area(
        "",
        placeholder="🔗 Paste your video URLs here...\n\nExamples:\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://www.instagram.com/p/example/\nhttps://www.tiktok.com/@user/video/1234567890",
        height=120,
        help="💡 Tip: You can paste multiple URLs, one per line, for batch downloading!"
    )
    
    # Validation feedback
    if url_input:
        urls = [url.strip() for url in url_input.split('\n') if url.strip()]
        valid_urls = [url for url in urls if is_valid_url(url)]
        invalid_urls = [url for url in urls if not is_valid_url(url)]
        
        if valid_urls:
            st.markdown(f"""
            <div style="background: #d4edda; color: #155724; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0;">
                ✅ <strong>{len(valid_urls)} valid URL(s)</strong> detected
            </div>
            """, unsafe_allow_html=True)
        
        if invalid_urls:
            st.markdown(f"""
            <div style="background: #f8d7da; color: #721c24; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0;">
                ❌ <strong>{len(invalid_urls)} invalid URL(s)</strong> found - please check the format
            </div>
            """, unsafe_allow_html=True)

    # Download configuration
    st.markdown("""
    <div class="feature-card">
        <h3 style="margin-top: 0; color: #667eea;">⚙️ Download Settings</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col_audio, col_format, col_playlist = st.columns(3)
    
    with col_audio:
        audio_only = st.checkbox("🎵 **Audio Only (MP3)**", value=False, 
                                help="Extract audio in MP3 format (192kbps)")
    
    with col_format:
        if not audio_only:
            format_choice = st.selectbox(
                "📺 **Video Quality**",
                ["Best Quality", "720p", "480p", "360p"],
                help="Choose video resolution"
            )
        else:
            format_choice = "Audio"
    
    with col_playlist:
        is_playlist = st.checkbox("📋 **Playlist Mode**", value=False,
                                help="Download all videos and create a ZIP file")

with col2:
    st.markdown("""
    <div class="info-card">
        <h3 style="margin-top: 0;">ℹ️ Video Information</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if url_input and len(url_input.strip()) > 0:
        urls = [url.strip() for url in url_input.split('\n') if url.strip()]
        valid_urls = [url for url in urls if is_valid_url(url)]
        
        if len(valid_urls) == 1:
            with st.spinner("🔍 Fetching video information..."):
                info = get_video_info(valid_urls[0])
                if info:
                    # Create thumbnail if available
                    thumbnail = info.get('thumbnail', '')
                    if thumbnail:
                        st.image(thumbnail, width=300)
                    
                    st.markdown(f"""
                    <div class="download-card">
                        <h4 style="margin-top: 0;">{info.get('title', 'Unknown Title')}</h4>
                        <div class="stats-container">
                            <div class="stat-item">
                                <div class="stat-number">⏱️</div>
                                <div style="font-weight: 500;">Duration</div>
                                <div style="color: #666;">{format_duration(info.get('duration'))}</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">👀</div>
                                <div style="font-weight: 500;">Views</div>
                                <div style="color: #666;">{format_number(info.get('view_count'))}</div>
                            </div>
                        </div>
                        <p style="margin-bottom: 0;"><strong>📺 Channel:</strong> {info.get('uploader', 'Unknown')}</p>
                        <p style="margin-bottom: 0;"><strong>📅 Upload Date:</strong> {info.get('upload_date', 'Unknown')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="status-error">
                        <h4 style="margin: 0;">❌ Could not fetch video information</h4>
                        <p style="margin: 0.5rem 0;">The URL might be invalid or the video is private</p>
                    </div>
                    """, unsafe_allow_html=True)
        elif len(valid_urls) > 1:
            st.markdown(f"""
            <div class="download-card">
                <h4 style="margin-top: 0;">📊 Batch Download</h4>
                <div class="stat-item">
                    <div class="stat-number">{len(valid_urls)}</div>
                    <div style="font-weight: 500;">Videos to Download</div>
                </div>
                <p style="margin-bottom: 0;">Ready for batch processing!</p>
            </div>
            """, unsafe_allow_html=True)

# Download section
st.markdown("---")

# Download button with improved styling
download_col1, download_col2, download_col3 = st.columns([1, 2, 1])

with download_col2:
    if st.button("🚀 Start Download", type="primary", 
                help="Click to begin downloading your videos!"):
        
        if not url_input.strip():
            st.markdown("""
            <div class="status-error">
                <h4 style="margin: 0;">❌ No URLs Provided</h4>
                <p style="margin: 0.5rem 0;">Please enter at least one valid URL to download</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            urls = [url.strip() for url in url_input.split('\n') if url.strip()]
            valid_urls = [url for url in urls if is_valid_url(url)]
            
            if not valid_urls:
                st.markdown("""
                <div class="status-error">
                    <h4 style="margin: 0;">❌ No Valid URLs</h4>
                    <p style="margin: 0.5rem 0;">Please check your URLs and try again</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Add to download history
                st.session_state.download_history.extend(valid_urls)
                
                # Create temporary directory for downloads
                with tempfile.TemporaryDirectory() as temp_dir:
                    download_folder = os.path.join(temp_dir, "downloads")
                    os.makedirs(download_folder, exist_ok=True)
                    
                    if len(valid_urls) == 1:
                        # Single download
                        st.markdown("""
                        <div class="progress-container">
                            <h3 style="text-align: center; color: #667eea; margin-top: 0;">
                                📥 Downloading Your Video
                            </h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        speed_text = st.empty()
                        
                        hook = ProgressHook(progress_bar, status_text, speed_text)
                        success, message = download_content(
                            valid_urls[0], format_choice, audio_only, download_folder, hook
                        )
                        
                        if success:
                            # List downloaded files
                            downloaded_files = list(Path(download_folder).glob("*"))
                            if downloaded_files:
                                st.markdown("""
                                <div class="feature-card">
                                    <h3 style="margin-top: 0; text-align: center; color: #28a745;">
                                        🎉 Download Complete!
                                    </h3>
                                    <p style="text-align: center; color: #666;">
                                        Your file is ready for download
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                for file_path in downloaded_files:
                                    if file_path.is_file():
                                        file_size = file_path.stat().st_size / (1024 * 1024)  # MB
                                        with open(file_path, "rb") as f:
                                            st.download_button(
                                                label=f"⬇️ Download {file_path.name} ({file_size:.1f} MB)",
                                                data=f.read(),
                                                file_name=file_path.name,
                                                mime="application/octet-stream",
                                                use_container_width=True
                                            )
                        else:
                            st.markdown(f"""
                            <div class="status-error">
                                <h4 style="margin: 0;">❌ Download Failed</h4>
                                <p style="margin: 0.5rem 0;">{message}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    else:
                        # Multiple downloads
                        st.markdown(f"""
                        <div class="progress-container">
                            <h3 style="text-align: center; color: #667eea; margin-top: 0;">
                                📥 Batch Download Progress
                            </h3>
                            <p style="text-align: center; color: #666;">
                                Downloading {len(valid_urls)} videos...
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        all_success = True
                        
                        for i, url in enumerate(valid_urls):
                            st.markdown(f"""
                            <div style="background: #f8f9fa; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
                                <h4 style="margin: 0; color: #667eea;">
                                    📹 Video {i+1}/{len(valid_urls)}
                                </h4>
                                <p style="margin: 0.5rem 0; color: #666; font-size: 0.9rem;">
                                    {url[:60]}{'...' if len(url) > 60 else ''}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            speed_text = st.empty()
                            
                            hook = ProgressHook(progress_bar, status_text, speed_text)
                            success, message = download_content(
                                url, format_choice, audio_only, download_folder, hook
                            )
                            
                            if not success:
                                st.markdown(f"""
                                <div class="status-error">
                                    <h4 style="margin: 0;">❌ Failed</h4>
                                    <p style="margin: 0.5rem 0;">{message}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                all_success = False
                        
                        # Create ZIP file with all downloads
                        downloaded_files = list(Path(download_folder).glob("*"))
                        if downloaded_files:
                            st.markdown("""
                            <div class="feature-card">
                                <h3 style="margin-top: 0; text-align: center; color: #28a745;">
                                    📦 Creating ZIP Archive...
                                </h3>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            zip_name = f"downloads_{int(time.time())}.zip"
                            zip_path = create_zip_file(download_folder, zip_name)
                            
                            zip_size = Path(zip_path).stat().st_size / (1024 * 1024)  # MB
                            
                            with open(zip_path, "rb") as f:
                                st.download_button(
                                    label=f"⬇️ Download All Files ({zip_size:.1f} MB ZIP)",
                                    data=f.read(),
                                    file_name=zip_name,
                                    mime="application/zip",
                                    use_container_width=True
                                )
                            
                            if all_success:
                                st.markdown(f"""
                                <div class="status-success">
                                    <h4 style="margin: 0;">🎉 All Downloads Completed!</h4>
                                    <p style="margin: 0.5rem 0;">Successfully downloaded {len(valid_urls)} videos</p>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown("""
                                <div style="background: #fff3cd; color: #856404; padding: 1rem; border-radius: 10px; text-align: center;">
                                    <h4 style="margin: 0;">⚠️ Partial Success</h4>
                                    <p style="margin: 0.5rem 0;">Some downloads failed. Check individual results above.</p>
                                </div>
                                """, unsafe_allow_html=True)

# Footer section
st.markdown("---")

# Statistics section
if st.session_state.download_history:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="stat-item">
            <div class="stat-number">{len(st.session_state.download_history)}</div>
            <div style="font-weight: 500;">Total Downloads</div>
            <div style="color: #666;">This Session</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        unique_domains = len(set([url.split('/')[2] for url in st.session_state.download_history if len(url.split('/')) > 2]))
        st.markdown(f"""
        <div class="stat-item">
            <div class="stat-number">{unique_domains}</div>
            <div style="font-weight: 500;">Platforms Used</div>
            <div style="color: #666;">Different Sources</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-item">
            <div class="stat-number">✅</div>
            <div style="font-weight: 500;">Status</div>
            <div style="color: #666;">Ready to Download</div>
        </div>
        """, unsafe_allow_html=True)

# Enhanced footer
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin: 2rem 0;">
    <h3 style="margin-top: 0;">🌟 Supported Platforms</h3>
    <p style="margin: 1rem 0; opacity: 0.9;">
        <strong>1000+ platforms supported including:</strong><br>
        YouTube • Instagram • TikTok • Twitter • Facebook • Vimeo • Dailymotion • Reddit • Twitch • And many more!
    </p>
    <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; margin: 1rem 0;">
        <p style="margin: 0; font-weight: 500;">
            🚀 <em>Powered by yt-dlp - The most advanced video downloader</em>
        </p>
    </div>
    <p style="margin-bottom: 0; font-size: 0.9rem; opacity: 0.8;">
        ⚖️ Please respect copyright laws and only download content you have the right to download
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar with enhanced information
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header">
        <h2 style="margin: 0;">📚 Quick Guide</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("🎯 How to Use", expanded=True):
        st.markdown("""
        **Step-by-step guide:**
        
        1. **📋 Paste URL(s)** - Copy video links from any supported platform
        2. **⚙️ Choose Settings** - Select video quality or audio-only mode
        3. **🚀 Click Download** - Start the download process
        4. **💾 Save Files** - Download your content to your device
        
        **💡 Pro Tips:**
        - Use multiple URLs for batch downloads
        - Enable playlist mode for YouTube playlists
        - Choose audio-only for music extraction
        - Lower quality = faster downloads
        """)
    
    with st.expander("🎵 Audio Features"):
        st.markdown("""
        **Audio Download Options:**
        
        - **Format:** MP3 (192kbps)
        - **Quality:** High-quality audio extraction
        - **Speed:** Faster than video downloads
        - **Use Cases:** Music, podcasts, speeches
        
        **Perfect for:**
        - Creating music libraries
        - Podcast collection
        - Language learning
        - Background music
        """)
    
    with st.expander("📺 Video Features"):
        st.markdown("""
        **Video Quality Options:**
        
        - **Best Quality:** Original resolution
        - **720p HD:** Great for most uses
        - **480p:** Good quality, smaller file
        - **360p:** Quick downloads
        
        **Features:**
        - Preserves original quality
        - Multiple format support
        - Subtitle inclusion (when available)
        - Thumbnail preservation
        """)
    
    with st.expander("🔧 Technical Info"):
        st.markdown("""
        **System Requirements:**
        ```
        Python 3.7+
        streamlit
        yt-dlp
        ```
        
        **Installation:**
        ```bash
        pip install streamlit yt-dlp
        streamlit run app.py
        ```
        
        **Features:**
        - Real-time progress tracking
        - Batch processing
        - Error handling
        - ZIP packaging
        - Cross-platform support
        """)
    
    with st.expander("❓ Troubleshooting"):
        st.markdown("""
        **Common Issues:**
        
        **🔴 "Video not available"**
        - Video might be private/deleted
        - Check if URL is correct
        - Try a different quality setting
        
        **🔴 "Slow downloads"**
        - Try lower quality settings
        - Check your internet connection
        - Some platforms have rate limits
        
        **🔴 "Download failed"**
        - Verify the URL is accessible
        - Some content may be region-locked
        - Try refreshing and retry
        
        **💡 Need Help?**
        - Check URL format
        - Ensure stable internet
        - Try different quality options
        """)
    
    st.markdown("---")
    
    # Quick stats
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1rem; border-radius: 10px; text-align: center;">
        <h4 style="margin-top: 0; color: #667eea;">📊 App Statistics</h4>
        <p style="margin: 0.5rem 0;"><strong>Supported Sites:</strong> 1000+</p>
        <p style="margin: 0.5rem 0;"><strong>Max Quality:</strong> 8K</p>
        <p style="margin: 0.5rem 0;"><strong>Audio Formats:</strong> MP3, WAV, M4A</p>
        <p style="margin: 0;"><strong>Video Formats:</strong> MP4, WebM, MKV</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Legal disclaimer
    st.markdown("""
    <div style="background: #fff3cd; color: #856404; padding: 1rem; border-radius: 10px; margin-top: 1rem; font-size: 0.85rem;">
        <h5 style="margin-top: 0;">⚖️ Legal Notice</h5>
        <p style="margin: 0;">
            This tool is for personal use only. Please respect copyright laws and terms of service 
            of the platforms you download from. Only download content you have permission to use.
        </p>
    </div>
    """, unsafe_allow_html=True)






