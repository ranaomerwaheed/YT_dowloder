# app.py

from flask import Flask, request, jsonify, render_template, send_file
import yt_dlp
import os
import uuid 
import shutil 

app = Flask(__name__)

# عارضی ڈاؤن لوڈ فولڈر کا نام
DOWNLOAD_FOLDER = 'downloads'

# یہ فولڈر Render/Railway پر خود بخود بنے گا، لیکن local ٹیسٹ کے لیے ہم بنا سکتے ہیں
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# =======================================================
# 1. روٹ: مرکزی صفحہ
# =======================================================
@app.route('/')
def index():
    """مرکزی صفحہ HTML ٹیمپلیٹ دکھاتا ہے۔"""
    return render_template('index.html')

# =======================================================
# 2. روٹ: ویڈیو فارمیٹس حاصل کرنا
# =======================================================
@app.route('/get_formats', methods=['POST'])
def get_formats():
    """دیئے گئے یوٹیوب URL سے ویڈیو کے تمام دستیاب فارمیٹس کو نکالتا ہے۔"""
    video_url = request.json.get('url')
    if not video_url:
        return jsonify({'error': 'URL فراہم نہیں کیا گیا'}), 400

    ydl_opts = {
        'skip_download': True,
        'simulate': True,
        'quiet': True,
        'force_generic_extractor': True,
        'format': 'bestvideo+bestaudio/best', 
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            available_formats = []
            
            # ویڈیو فارمیٹس (4K, 1080p وغیرہ)
            for f in info_dict.get('formats', []):
                if f.get('height') and f.get('ext') in ['mp4', 'webm']:
                    quality = f'{f["height"]}p'
                    
                    # یہ یقینی بناتا ہے کہ ہم صحیح format ID استعمال کر رہے ہیں
                    if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                        format_id_combined = f'{f["format_id"]}+bestaudio'
                    else:
                         format_id_combined = f['format_id']
                         
                    available_formats.append({
                        'quality': quality,
                        'format_id': format_id_combined,
                        'ext': 'mp4', 
                        'note': f.get('note', '')
                    })
            
            # آڈیو فارمیٹ (MP3)
            audio_format = {
                'quality': 'MP3 (Audio Only)',
                'format_id': 'bestaudio', 
                'ext': 'mp3',
                'note': 'Highest quality audio only'
            }
            available_formats.append(audio_format)
            
            # صفائی اور ترتیب
            unique_formats = {frozenset(d.items()): d for d in available_formats}
            final_formats = list(unique_formats.values())
            final_formats.sort(key=lambda x: int(x['quality'].replace('p', '')) if 'p' in x['quality'] else -1, reverse=True)

            response = {
                'title': info_dict.get('title', 'Unknown Title'),
                'thumbnail': info_dict.get('thumbnail', ''),
                'formats': final_formats
            }
            return jsonify(response)
            
    except Exception as e:
        return jsonify({'error': f'معلومات حاصل نہیں ہو سکیں: {str(e)}'}), 500

# =======================================================
# 3. روٹ: فائل ڈاؤن لوڈ کرنا (اصل کام)
# =======================================================
@app.route('/download', methods=['POST'])
def download_file():
    """مطلوبہ فارمیٹ ID کا استعمال کرتے ہوئے فائل کو ڈاؤن لوڈ کرتا ہے۔"""
    data = request.json
    video_url = data.get('url')
    format_id = data.get('format_id')
    quality = data.get('quality')

    if not video_url or not format_id:
        return jsonify({'error': 'URL یا فارمیٹ ID غائب ہے'}), 400

    temp_dir_name = str(uuid.uuid4())
    temp_download_path = os.path.join(DOWNLOAD_FOLDER, temp_dir_name)
    os.makedirs(temp_download_path, exist_ok=True)
    outtmpl = os.path.join(temp_download_path, 'output.%(ext)s')

    ydl_opts = {
        'format': format_id, 
        'outtmpl': outtmpl, 
        'noplaylist': True,
        'quiet': True,
        'merge_output_format': 'mp4', # زیادہ تر کوالٹیز کے لیے mp4 کو ترجیح دیں
    }

    downloaded_file = None
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            
            title = info_dict.get('title', 'youtube_video').replace(' ', '_')
            
            for f in os.listdir(temp_download_path):
                if f.startswith('output'):
                    downloaded_file = os.path.join(temp_download_path, f)
                    break
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                raise Exception("ڈاؤن لوڈ فائل کو عارضی فولڈر میں نہیں ڈھونڈا جا سکا۔")

            ext = downloaded_file.split('.')[-1]
            final_filename = f"{title}_{quality}.{ext}"
            
            response = send_file(
                downloaded_file,
                as_attachment=True,
                download_name=final_filename,
                mimetype=f'video/{ext}' if ext != 'mp3' else 'audio/mpeg'
            )
            
            # فائل بھیجنے کے بعد عارضی فولڈر کو ڈیلیٹ کر دیں (سرور کی جگہ صاف رکھنے کے لیے)
            @response.call_on_close
            def after_response():
                try:
                    shutil.rmtree(temp_download_path)
                except Exception as e:
                    print(f"فولڈر ڈیلیٹ کرتے ہوئے ایرر: {e}")
                    
            return response

    except Exception as e:
        try:
             if os.path.exists(temp_download_path):
                shutil.rmtree(temp_download_path)
        except:
            pass
            
        return jsonify({'error': f'ڈاؤن لوڈ ایرر: {str(e)}'}), 500

if __name__ == '__main__':
    # Local ٹیسٹنگ کے لیے
    app.run(debug=True)