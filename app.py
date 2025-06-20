from flask import Flask, request, send_file, render_template, jsonify
import yt_dlp
import uuid
import os
import threading
import time
import requests
from urllib.parse import urlparse
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static'
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Supported platforms
SUPPORTED_PLATFORMS = {
    'youtube.com': 'YouTube',
    'youtu.be': 'YouTube',
    'tiktok.com': 'TikTok',
    'instagram.com': 'Instagram',
    'facebook.com': 'Facebook',
    'fb.watch': 'Facebook',
    'twitter.com': 'Twitter',
    'x.com': 'Twitter',
    'vimeo.com': 'Vimeo',
    'dailymotion.com': 'Dailymotion',
    'twitch.tv': 'Twitch'
}

def detect_platform(url):
    """Detect platform from URL"""
    try:
        domain = urlparse(url).netloc.lower()
        for platform_domain, platform_name in SUPPORTED_PLATFORMS.items():
            if platform_domain in domain:
                return platform_name
        return 'Generic'
    except:
        return 'Unknown'

def get_platform_specific_options(platform):
    """Get platform-specific yt-dlp options"""
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'extractaudio': False,
        'retries': 10,
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,
        'http_chunk_size': 10485760,
    }

    if platform == 'TikTok':
        base_opts.update({
            'format': 'best[height<=720]/best',
            'cookiesfrombrowser': ('chrome',),
        })
    elif platform == 'Instagram':
        base_opts.update({
            'format': 'best[height<=720]/best',
            'cookiesfrombrowser': ('chrome',),
        })
    elif platform == 'YouTube':
        base_opts.update({
            'format': 'best[height<=720]/best[height<=480]/worst',
        })
    elif platform == 'Facebook':
        base_opts.update({
            'format': 'best[height<=720]/best',
        })
    elif platform == 'Twitter':
        base_opts.update({
            'format': 'best[height<=720]/best',
        })
    else:
        base_opts.update({
            'format': 'best[height<=720]/best',
        })

    return base_opts

def download_video(url, filename, platform):
    """Universal video download function"""
    try:
        ydl_opts = get_platform_specific_options(platform)
        ydl_opts['outtmpl'] = filename

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                ydl.download([url])
                return True
            return False

    except Exception as e:
        print(f"Download error for {platform}: {e}")
        try:
            fallback_opts = {
                'outtmpl': filename,
                'format': 'best/worst',
                'quiet': True,
                'retries': 5
            }
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                ydl.download([url])
                return True
        except Exception as fallback_error:
            print(f"Fallback download also failed: {fallback_error}")
            return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'URL required'}), 400

    try:
        platform = detect_platform(url)
        ydl_opts = get_platform_specific_options(platform)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get('title', f'{platform} Video')
        thumbnail = info.get('thumbnail', '')
        duration = info.get('duration', 0)
        uploader = info.get('uploader', 'Unknown')

        safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
        timestamp = int(time.time())
        filename = f"{platform}_{safe_title}_{timestamp}.mp4"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        download_thread = threading.Thread(
            target=download_video,
            args=(url, filepath, platform)
        )
        download_thread.start()

        return jsonify({
            'filename': filename,
            'title': title,
            'thumbnail': thumbnail,
            'platform': platform,
            'uploader': uploader,
            'duration': duration
        })

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return jsonify({'error': f'Failed to process {platform} video: {str(e)}'}), 500

@app.route('/downloads/<filename>')
def download_file(filename):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        max_wait = 120
        wait_time = 0

        while not os.path.exists(filepath) and wait_time < max_wait:
            time.sleep(2)
            wait_time += 2

        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not ready, try again in a moment'}), 202

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def cleanup_old_files():
    try:
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            return

        current_time = time.time()
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getctime(filepath)
                if file_age > 3600:
                    os.remove(filepath)
                    print(f"Cleaned up old file: {filename}")
    except Exception as e:
        print(f"Cleanup error: {e}")

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    cleanup_old_files()
    app.run(debug=True)
