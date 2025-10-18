# app.py - فایل اصلی Flask
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import threading
import os
import json
from datetime import datetime

# ایمپورت ماژول‌های پروژه
from modules.gpio_controller import GPIOController
from modules.phone_controller import PhoneController
from modules.ai_chat import AIChat
from modules.music_player import MusicPlayer
from modules.alarm_manager import AlarmManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'study-assistant-secret-key-2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize controllers
gpio_controller = GPIOController()
phone_controller = PhoneController()
ai_chat = AIChat()
music_player = MusicPlayer(phone_controller)
alarm_manager = AlarmManager()

@app.route('/')
def index():
    """صفحه اصلی"""
    return render_template('index.html')

@app.route('/light-control')
def light_control():
    """کنترل چراغ"""
    return render_template('light_control.html')

@app.route('/music-player')
def music_player_page():
    """پخش موسیقی"""
    return render_template('music_player.html')

@app.route('/photo-processor')
def photo_processor():
    """پردازش تصویر"""
    return render_template('photo_processor.html')

@app.route('/ai-chat')
def ai_chat_page():
    """چت هوش مصنوعی"""
    return render_template('ai_chat.html')

@app.route('/alarm-setter')
def alarm_setter():
    """تنظیم آلارم"""
    return render_template('alarm_setter.html')

# =============================================================================
# API Routes برای کنترل چراغ
# =============================================================================

@app.route('/api/light/on', methods=['POST'])
def light_on():
    try:
        gpio_controller.light_on()
        return jsonify({'status': 'success', 'message': 'چراغ روشن شد'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/light/off', methods=['POST'])
def light_off():
    try:
        gpio_controller.light_off()
        return jsonify({'status': 'success', 'message': 'چراغ خاموش شد'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/light/brightness', methods=['POST'])
def set_brightness():
    try:
        brightness = request.json.get('brightness', 50)
        gpio_controller.set_brightness(brightness)
        return jsonify({'status': 'success', 'message': f'روشنایی تنظیم شد: {brightness}%'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# =============================================================================
# API Routes برای موسیقی
# =============================================================================

@app.route('/api/music/play', methods=['POST'])
def play_music():
    try:
        music_file = request.json.get('file')
        success = music_player.play(music_file)
        if success:
            return jsonify({'status': 'success', 'message': 'آهنگ در حال پخش'})
        else:
            return jsonify({'status': 'error', 'message': 'خطا در پخش آهنگ'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/music/stop', methods=['POST'])
def stop_music():
    try:
        music_player.stop()
        return jsonify({'status': 'success', 'message': 'توقف پخش'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/music/list')
def get_music_list():
    try:
        music_list = music_player.get_music_list()
        return jsonify({'status': 'success', 'data': music_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# =============================================================================
# API Routes برای چت هوش مصنوعی
# =============================================================================

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat_endpoint():
    try:
        message = request.json.get('message')
        response = ai_chat.send_message(message)
        return jsonify({'status': 'success', 'response': response})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# =============================================================================
# API Routes برای آلارم
# =============================================================================

@app.route('/api/alarm/set', methods=['POST'])
def set_alarm():
    try:
        hour = request.json.get('hour')
        minute = request.json.get('minute')
        success = alarm_manager.set_alarm(hour, minute)
        if success:
            return jsonify({'status': 'success', 'message': 'آلارم تنظیم شد'})
        else:
            return jsonify({'status': 'error', 'message': 'خطا در تنظیم آلارم'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/alarm/stop', methods=['POST'])
def stop_alarm():
    try:
        alarm_manager.stop_alarm()
        return jsonify({'status': 'success', 'message': 'آلارم متوقف شد'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# =============================================================================
# WebSocket برای ارتباط بلادرنگ
# =============================================================================

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'message': 'Connected to Study Assistant'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# =============================================================================
# Route برای دریافت زمان ایران
# =============================================================================

@app.route('/api/time/iran')
def get_iran_time():
    try:
        from utils.helpers import get_iran_time
        time_str = get_iran_time()
        return jsonify({'status': 'success', 'time': time_str})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# =============================================================================
# Route برای آپلود فایل
# =============================================================================

@app.route('/api/upload/photo', methods=['POST'])
def upload_photo():
    try:
        if 'photo' not in request.files:
            return jsonify({'status': 'error', 'message': 'هیچ فایلی انتخاب نشده'})
        
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'نام فایل نامعتبر'})
        
        # ذخیره فایل
        filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'photos', filename)
        file.save(filepath)
        
        return jsonify({'status': 'success', 'filename': filename})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# =============================================================================
# Route اصلی برای اجرا
# =============================================================================

if __name__ == '__main__':
    # ایجاد پوشه‌های لازم
    os.makedirs('uploads/photos', exist_ok=True)
    os.makedirs('uploads/music', exist_ok=True)
    
    print("🎯 دستیار مطالعه هوشمند - نسخه وب")
    print("🌐 در حال راه‌اندازی سرور...")
    print("📱 دسترسی از: http://0.0.0.0:5000")
    
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5000, 
        debug=False,
        allow_unsafe_werkzeug=True
    )