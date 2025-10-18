# modules/__init__.py
"""
ماژول‌های دستیار مطالعه هوشمند
"""

from .gpio_controller import GPIOController
from .phone_controller import PhoneController
from .ai_chat import AIChat
from .music_player import MusicPlayer
from .alarm_manager import AlarmManager

__all__ = [
    'GPIOController',
    'PhoneController', 
    'AIChat',
    'MusicPlayer',
    'AlarmManager'
]

__version__ = '1.0.0'
__author__ = 'Study Assistant Team'
__description__ = 'ماژول‌های اصلی دستیار مطالعه هوشمند'