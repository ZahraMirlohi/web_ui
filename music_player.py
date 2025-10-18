# music_player.py
import os
import logging
import subprocess
import time
import threading
from datetime import datetime
from phone.controller import PhoneController

class MusicPlayer:
    def __init__(self, phone_controller=None):
        self.phone_controller = phone_controller or PhoneController()
        self.logger = logging.getLogger(__name__)
        self.current_track = None
        self.is_playing = False
        self.volume_level = 80
        self.playlist = []
        self.current_index = -1
        
        # مسیرهای موسیقی
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.music_dir = os.path.join(self.base_dir, '..', 'uploads', 'music')
        
        # ایجاد پوشه موسیقی اگر وجود ندارد
        os.makedirs(self.music_dir, exist_ok=True)
        
        self.logger.info("Music Player initialized")

    def get_music_list(self):
        """دریافت لیست فایل‌های موسیقی"""
        try:
            music_files = []
            
            if os.path.exists(self.music_dir):
                for file in os.listdir(self.music_dir):
                    if file.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a', '.flac')):
                        file_path = os.path.join(self.music_dir, file)
                        file_info = {
                            'filename': file,
                            'path': file_path,
                            'size': os.path.getsize(file_path),
                            'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                        }
                        music_files.append(file_info)
            
            self.playlist = sorted(music_files, key=lambda x: x['filename'])
            self.logger.info(f"Found {len(music_files)} music files")
            return [file['filename'] for file in self.playlist]
            
        except Exception as e:
            self.logger.error(f"Error getting music list: {e}")
            return []

    def play(self, music_file, volume=None):
        """پخش فایل موسیقی"""
        try:
            # توقف پخش قبلی
            self.stop()
            
            # پیدا کردن مسیر کامل فایل
            file_path = self._find_music_file(music_file)
            if not file_path:
                self.logger.error(f"Music file not found: {music_file}")
                return False
            
            self.current_track = music_file
            self.current_index = self._get_file_index(music_file)
            
            # تنظیم حجم صدا
            if volume is not None:
                self.volume_level = volume
                self._set_volume(volume)
            
            # پخش از طریق کنترلر گوشی
            success = self.phone_controller.play_music(file_path)
            
            if success:
                self.is_playing = True
                self.logger.info(f"Now playing: {music_file}")
                
                # شروع مانیتورینگ وضعیت پخش
                self._start_playback_monitor()
                
                return True
            else:
                self.logger.error(f"Failed to play: {music_file}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error playing music: {e}")
            return False

    def stop(self):
        """توقف پخش"""
        try:
            success = self.phone_controller.stop_all_media()
            
            if success:
                self.is_playing = False
                self.current_track = None
                self.logger.info("Playback stopped")
            else:
                self.logger.warning("Stop command sent but may not have worked")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error stopping playback: {e}")
            return False

    def pause(self):
        """توقف موقت پخش"""
        try:
            success = self.phone_controller.pause_media()
            
            if success:
                self.is_playing = False
                self.logger.info("Playback paused")
            else:
                self.logger.warning("Pause command may not have worked")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error pausing playback: {e}")
            return False

    def resume(self):
        """ادامه پخش"""
        try:
            success = self.phone_controller.play_media()
            
            if success:
                self.is_playing = True
                self.logger.info("Playback resumed")
            else:
                self.logger.warning("Resume command may not have worked")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error resuming playback: {e}")
            return False

    def set_volume(self, volume):
        """تنظیم حجم صدا"""
        try:
            if not 0 <= volume <= 100:
                raise ValueError("Volume must be between 0 and 100")
            
            self.volume_level = volume
            success = self._set_volume(volume)
            
            if success:
                self.logger.info(f"Volume set to {volume}%")
            else:
                self.logger.warning("Volume setting may not have worked")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error setting volume: {e}")
            return False

    def volume_up(self, increment=10):
        """افزایش حجم صدا"""
        new_volume = min(100, self.volume_level + increment)
        return self.set_volume(new_volume)

    def volume_down(self, decrement=10):
        """کاهش حجم صدا"""
        new_volume = max(0, self.volume_level - decrement)
        return self.set_volume(new_volume)

    def next_track(self):
        """پخش آهنگ بعدی"""
        if not self.playlist:
            self.logger.warning("No tracks in playlist")
            return False
        
        next_index = (self.current_index + 1) % len(self.playlist)
        next_track = self.playlist[next_index]['filename']
        
        return self.play(next_track)

    def previous_track(self):
        """پخش آهنگ قبلی"""
        if not self.playlist:
            self.logger.warning("No tracks in playlist")
            return False
        
        prev_index = (self.current_index - 1) % len(self.playlist)
        prev_track = self.playlist[prev_index]['filename']
        
        return self.play(prev_track)

    def get_playback_status(self):
        """دریافت وضعیت پخش"""
        try:
            is_playing = self.phone_controller.is_music_playing()
            self.is_playing = is_playing
            
            status = {
                'is_playing': is_playing,
                'current_track': self.current_track,
                'volume': self.volume_level,
                'playlist_length': len(self.playlist),
                'current_index': self.current_index,
                'playlist': [track['filename'] for track in self.playlist]
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting playback status: {e}")
            return {
                'is_playing': False,
                'current_track': None,
                'volume': self.volume_level,
                'playlist_length': 0,
                'current_index': -1,
                'playlist': []
            }

    def control_playback(self, action):
        """کنترل پخش با دستورات مختلف"""
        actions = {
            'play': self.resume,
            'pause': self.pause,
            'stop': self.stop,
            'next': self.next_track,
            'previous': self.previous_track,
            'volume_up': lambda: self.volume_up(10),
            'volume_down': lambda: self.volume_down(10),
            'mute': lambda: self.set_volume(0),
            'unmute': lambda: self.set_volume(80)
        }
        
        if action not in actions:
            self.logger.error(f"Unknown playback action: {action}")
            return False
        
        try:
            return actions[action]()
        except Exception as e:
            self.logger.error(f"Error executing action {action}: {e}")
            return False

    def create_playlist(self, track_list):
        """ایجاد لیست پخش سفارشی"""
        try:
            self.playlist = []
            for track in track_list:
                file_path = self._find_music_file(track)
                if file_path:
                    file_info = {
                        'filename': track,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self.playlist.append(file_info)
            
            self.current_index = -1
            self.logger.info(f"Playlist created with {len(self.playlist)} tracks")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating playlist: {e}")
            return False

    def shuffle_playlist(self):
        """تصادفی کردن لیست پخش"""
        import random
        try:
            random.shuffle(self.playlist)
            self.current_index = -1
            self.logger.info("Playlist shuffled")
            return True
        except Exception as e:
            self.logger.error(f"Error shuffling playlist: {e}")
            return False

    def get_current_track_info(self):
        """دریافت اطلاعات آهنگ در حال پخش"""
        if not self.current_track or self.current_index == -1:
            return None
        
        try:
            track_info = self.playlist[self.current_index].copy()
            track_info['is_playing'] = self.is_playing
            track_info['volume'] = self.volume_level
            return track_info
        except Exception as e:
            self.logger.error(f"Error getting track info: {e}")
            return None

    def _find_music_file(self, filename):
        """پیدا کردن مسیر کامل فایل موسیقی"""
        possible_paths = [
            os.path.join(self.music_dir, filename),
            os.path.join(self.music_dir, filename.lower()),
            os.path.join(self.music_dir, filename.upper())
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None

    def _get_file_index(self, filename):
        """دریافت ایندکس فایل در لیست پخش"""
        for i, track in enumerate(self.playlist):
            if track['filename'] == filename:
                return i
        return -1

    def _set_volume(self, volume):
        """تنظیم حجم صدا از طریق ADB"""
        try:
            # تبدیل حجم 0-100 به مقیاس 0-15 سیستم اندروید
            android_volume = int((volume / 100) * 15)
            
            result = subprocess.run([
                'adb', 'shell', 'media', 'volume', '--stream', '3', '--set', str(android_volume)
            ], capture_output=True, text=True, timeout=10)
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Error setting volume via ADB: {e}")
            return False

    def _start_playback_monitor(self):
        """شروع مانیتورینگ وضعیت پخش"""
        def monitor():
            while self.is_playing:
                try:
                    time.sleep(5)  # چک هر 5 ثانیه
                    
                    # بررسی وضعیت پخش
                    is_still_playing = self.phone_controller.is_music_playing()
                    
                    if not is_still_playing and self.is_playing:
                        self.logger.info("Playback ended naturally")
                        self.is_playing = False
                        
                        # پخش آهنگ بعدی اگر در حالت پخش لیست هستیم
                        if self.playlist and self.current_index != -1:
                            self.next_track()
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error in playback monitor: {e}")
                    break

        # شروع مانیتورینگ در thread جداگانه
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

    def cleanup(self):
        """تمیزکاری منابع"""
        try:
            self.stop()
            self.logger.info("Music Player cleaned up")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

# تست مستقل
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎵 Testing Music Player...")
    
    try:
        player = MusicPlayer()
        
        # دریافت لیست موسیقی
        print("1. Getting music list...")
        music_list = player.get_music_list()
        print(f"Found {len(music_list)} tracks: {music_list}")
        
        if music_list:
            # تست پخش اگر فایل موسیقی وجود دارد
            test_track = music_list[0]
            print(f"2. Testing playback of: {test_track}")
            
            success = player.play(test_track, volume=50)
            print(f"Play started: {success}")
            
            if success:
                time.sleep(5)  # پخش برای 5 ثانیه
                
                # تست کنترل‌ها
                print("3. Testing controls...")
                player.pause()
                time.sleep(2)
                player.resume()
                time.sleep(2)
                player.volume_up()
                time.sleep(1)
                player.volume_down()
                time.sleep(1)
                
                # تست وضعیت
                print("4. Testing status...")
                status = player.get_playback_status()
                print(f"Playback Status: {status}")
                
                # توقف
                print("5. Stopping playback...")
                player.stop()
                
        else:
            print("No music files found for testing")
        
        # تست کنترل‌های عمومی
        print("6. Testing general controls...")
        player.control_playback('volume_up')
        player.control_playback('volume_down')
        
        print("✅ Music Player test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        player.cleanup()