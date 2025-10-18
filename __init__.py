# __init__.py
"""
دستیار مطالعه هوشمند - سیستم یکپارچه مدیریت مطالعه

یک سیستم کامل برای مدیریت محیط مطالعه شامل:
• کنترل هوشمند چراغ مطالعه
• پخش موسیقی آرامش‌بخش  
• پردازش تصویر و استخراج متن
• دستیار هوش مصنوعی برای پاسخ به سوالات
• سیستم هشدار و مدیریت زمان
"""

__version__ = '1.0.0'
__author__ = 'Study Assistant Team'
__email__ = 'support@study-assistant.com'
__license__ = 'MIT'
__description__ = 'سیستم یکپارچه مدیریت مطالعه مبتنی بر رزبری پای'

import os
import sys

# اضافه کردن مسیر ماژول‌ها به PATH
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'config'))

def get_version():
    """دریافت نسخه برنامه"""
    return __version__

def get_system_info():
    """دریافت اطلاعات سیستم"""
    import platform
    return {
        'version': __version__,
        'python_version': platform.python_version(),
        'os': platform.system(),
        'os_version': platform.release(),
        'architecture': platform.architecture()[0]
    }

def check_dependencies():
    """بررسی وابستگی‌های سیستم"""
    dependencies = {
        'Flask': '2.3.3',
        'Flask-SocketIO': '5.3.6', 
        'RPi.GPIO': '0.7.1',
        'Pillow': '10.0.1',
        'requests': '2.31.0'
    }
    
    missing = []
    for package, version in dependencies.items():
        try:
            mod = __import__(package)
            if hasattr(mod, '__version__'):
                installed_version = mod.__version__
                if installed_version < version:
                    missing.append(f"{package} (requires {version}, found {installed_version})")
            else:
                missing.append(f"{package} (version check failed)")
        except ImportError:
            missing.append(f"{package} (not installed)")
    
    return missing

# ایمپورت کلاس‌های اصلی برای دسترسی آسان
try:
    from modules.gpio_controller import GPIOController
    from modules.phone_controller import PhoneController
    from modules.ai_chat import AIChat
    from modules.music_player import MusicPlayer
    from modules.alarm_manager import AlarmManager
except ImportError as e:
    print(f"Warning: Could not import main modules: {e}")

# ایجاد پوشه‌های لازم در هنگام ایمپورت
def _create_required_dirs():
    """ایجاد پوشه‌های مورد نیاز"""
    import os
    required_dirs = [
        'uploads',
        'uploads/photos', 
        'uploads/music',
        'logs',
        'backups'
    ]
    
    for dir_path in required_dirs:
        full_path = os.path.join(os.path.dirname(__file__), dir_path)
        os.makedirs(full_path, exist_ok=True)

_create_required_dirs()

print(f"🎯 Study Assistant v{__version__} initialized successfully!")