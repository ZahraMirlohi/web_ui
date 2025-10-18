# phone_controller.py
import subprocess
import os
import time
import logging
import threading
from datetime import datetime

class PhoneController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.device_id = None
        self.adb_path = "adb"
        self.connection_monitor_thread = None
        self.monitor_running = False
        
        self._setup_adb()
        self._start_connection_monitor()
        self.logger.info("Phone Controller initialized")

    def _setup_adb(self):
        """تنظیمات اولیه ADB"""
        try:
            # بررسی وجود ADB
            result = subprocess.run([self.adb_path, 'version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info("ADB found successfully")
            else:
                self.logger.warning("ADB not found in PATH")
                self.adb_path = "/usr/bin/adb"  # مسیر پیش‌فرض در لینوکس
        except Exception as e:
            self.logger.error(f"Error setting up ADB: {e}")

    def _start_connection_monitor(self):
        """شروع مانیتورینگ اتصال گوشی"""
        self.monitor_running = True
        self.connection_monitor_thread = threading.Thread(target=self._connection_monitor, daemon=True)
        self.connection_monitor_thread.start()
        self.logger.info("Connection monitor started")

    def _connection_monitor(self):
        """مانیتورینگ وضعیت اتصال گوشی"""
        while self.monitor_running:
            try:
                previous_status = self.connected
                
                # بررسی اتصال
                result = subprocess.run([self.adb_path, 'devices'], 
                                      capture_output=True, text=True, timeout=10)
                
                if 'device' in result.stdout and 'unauthorized' not in result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # رد کردن خط اول
                        if 'device' in line and 'offline' not in line:
                            parts = line.split('\t')
                            if len(parts) >= 2 and parts[1] == 'device':
                                self.device_id = parts[0]
                                self.connected = True
                                break
                    else:
                        self.connected = False
                        self.device_id = None
                else:
                    self.connected = False
                    self.device_id = None
                
                # لاگ کردن تغییر وضعیت
                if previous_status != self.connected:
                    if self.connected:
                        self.logger.info(f"Phone connected: {self.device_id}")
                    else:
                        self.logger.warning("Phone disconnected")
                
                time.sleep(5)  # چک هر 5 ثانیه
                
            except Exception as e:
                self.logger.error(f"Error in connection monitor: {e}")
                self.connected = False
                time.sleep(10)  # در صورت خطا، تاخیر بیشتر

    def check_connection(self):
        """بررسی وضعیت اتصال"""
        return self.connected

    def run_command(self, command, timeout=15):
        """اجرای دستور ADB"""
        try:
            if not self.connected:
                self.logger.error("No device connected")
                return False, "No device connected"

            full_command = [self.adb_path, '-s', self.device_id] + command.split()
            
            result = subprocess.run(full_command, 
                                  capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0:
                self.logger.debug(f"Command executed successfully: {command}")
                return True, result.stdout
            else:
                self.logger.error(f"Command failed: {command} - {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timeout: {command}")
            return False, "Command timeout"
        except Exception as e:
            self.logger.error(f"Error executing command {command}: {e}")
            return False, str(e)

    def wake_screen(self):
        """روشن کردن صفحه گوشی"""
        commands = [
            "shell input keyevent KEYCODE_WAKEUP",
            "shell input keyevent KEYCODE_MENU",  # برای بیدار کردن کامل
            "shell input keyevent KEYCODE_POWER"  # روشن/خاموش کردن صفحه
        ]
        
        for command in commands:
            success, message = self.run_command(command)
            if success:
                self.logger.info("Screen woken up successfully")
                return True
        
        self.logger.error("Failed to wake screen")
        return False

    def turn_screen_off(self):
        """خاموش کردن صفحه گوشی"""
        success, message = self.run_command("shell input keyevent KEYCODE_POWER")
        if success:
            self.logger.info("Screen turned off")
        else:
            self.logger.error("Failed to turn screen off")
        return success

    def set_max_volume(self):
        """تنظیم حداکثر صدا"""
        try:
            # تنظیم صدا برای مدیا (استریم 3)
            commands = [
                "shell media volume --stream 3 --set 15",  # حداکثر صدا
                "shell media volume --stream 1 --set 15",  # صدا برای سیستم
            ]
            
            for command in commands:
                self.run_command(command)
            
            self.logger.info("Volume set to maximum")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting max volume: {e}")
            return False

    def set_volume(self, level):
        """تنظیم سطح صدا (0-100)"""
        try:
            if not 0 <= level <= 100:
                raise ValueError("Volume level must be between 0 and 100")
            
            # تبدیل به مقیاس 0-15 اندروید
            android_level = int((level / 100) * 15)
            
            success, message = self.run_command(f"shell media volume --stream 3 --set {android_level}")
            
            if success:
                self.logger.info(f"Volume set to {level}%")
                return True
            else:
                self.logger.error(f"Failed to set volume: {message}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting volume: {e}")
            return False

    def play_music(self, file_path):
        """پخش فایل موسیقی"""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Music file not found: {file_path}")
                return False

            filename = os.path.basename(file_path)
            remote_path = f"/sdcard/Music/{filename}"
            
            # انتقال فایل به گوشی
            success, message = self.run_command(f"push \"{file_path}\" \"{remote_path}\"", timeout=30)
            if not success:
                self.logger.error(f"Failed to transfer file: {message}")
                return False

            # پخش فایل
            success, message = self.run_command(
                f"shell am start -a android.intent.action.VIEW -d file://{remote_path} -t audio/*"
            )
            
            if success:
                self.logger.info(f"Music playback started: {filename}")
                return True
            else:
                self.logger.error(f"Failed to play music: {message}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error playing music: {e}")
            return False

    def play_alarm(self):
        """پخش صدای آلارم"""
        try:
            # روش‌های مختلف برای پخش آلارم
            methods = [
                # روش 1: استفاده از آلارم سیستم
                "shell am start -a android.intent.action.VIEW -d content://media/internal/audio/media/10",
                # روش 2: پخش فایل آلارم پیش‌فرض
                "shell am start -a android.intent.action.VIEW -d file:///system/media/audio/alarms/Alarm_Beep_03.ogg",
                # روش 3: استفاده از برنامه ساعت
                "shell am start -n com.android.deskclock/.AlarmAlert",
                # روش 4: پخش از طریق مدیا پلیر
                "shell input keyevent KEYCODE_MEDIA_PLAY"
            ]
            
            for method in methods:
                success, message = self.run_command(method)
                if success:
                    self.logger.info("Alarm sound started")
                    return True
            
            self.logger.error("All alarm methods failed")
            return False
            
        except Exception as e:
            self.logger.error(f"Error playing alarm: {e}")
            return False

    def stop_all_media(self):
        """توقف تمام پخش‌های مدیا"""
        try:
            commands = [
                "shell input keyevent KEYCODE_MEDIA_STOP",
                "shell input keyevent KEYCODE_MEDIA_PAUSE",
                "shell am force-stop com.android.music",  # توقف برنامه موسیقی
                "shell am force-stop com.android.deskclock",  # توقف برنامه ساعت
            ]
            
            for command in commands:
                self.run_command(command)
            
            self.logger.info("All media stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping media: {e}")
            return False

    def pause_media(self):
        """توقف موقت پخش"""
        success, message = self.run_command("shell input keyevent KEYCODE_MEDIA_PAUSE")
        if success:
            self.logger.info("Media paused")
        else:
            self.logger.error("Failed to pause media")
        return success

    def play_media(self):
        """ادامه پخش"""
        success, message = self.run_command("shell input keyevent KEYCODE_MEDIA_PLAY")
        if success:
            self.logger.info("Media playback resumed")
        else:
            self.logger.error("Failed to resume media")
        return success

    def is_music_playing(self):
        """بررسی آیا موسیقی در حال پخش است"""
        try:
            # بررسی فرآیندهای در حال اجرا
            success, output = self.run_command("shell ps | grep media")
            if success and "media" in output.lower():
                return True
            
            # بررسی وضعیت صدا
            success, output = self.run_command("shell dumpsys audio | grep -i 'stream music'")
            if success and "state:started" in output.lower():
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking music status: {e}")
            return False

    def start_vibration(self):
        """شروع ویبره"""
        try:
            # فعال کردن ویبره
            commands = [
                "shell vibrate on",
                "shell input keyevent KEYCODE_VOLUME_UP",  # برای اطمینان
            ]
            
            for command in commands:
                self.run_command(command)
            
            self.logger.info("Vibration started")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting vibration: {e}")
            return False

    def stop_vibration(self):
        """توقف ویبره"""
        success, message = self.run_command("shell vibrate off")
        if success:
            self.logger.info("Vibration stopped")
        else:
            self.logger.error("Failed to stop vibration")
        return success

    def capture_photo(self, save_path=None):
        """گرفتن عکس از دوربین گوشی"""
        try:
            if not save_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"/sdcard/DCIM/study_photo_{timestamp}.jpg"
            else:
                save_path = f"/sdcard/DCIM/{os.path.basename(save_path)}"

            # باز کردن دوربین
            self.run_command("shell am start -a android.media.action.IMAGE_CAPTURE")
            time.sleep(2)
            
            # گرفتن عکس
            self.run_command("shell input keyevent KEYCODE_CAMERA")
            time.sleep(3)
            
            # پیدا کردن آخرین عکس
            success, output = self.run_command("shell ls -t /sdcard/DCIM/Camera/*.jpg | head -1")
            if success and output.strip():
                latest_photo = output.strip()
                
                # انتقال عکس به سرور
                local_path = save_path if save_path.startswith('/') else f"/tmp/{os.path.basename(save_path)}"
                self.run_command(f"pull \"{latest_photo}\" \"{local_path}\"", timeout=30)
                
                self.logger.info(f"Photo captured and saved: {local_path}")
                return local_path
            
            self.logger.error("No photo found after capture")
            return None
            
        except Exception as e:
            self.logger.error(f"Error capturing photo: {e}")
            return None

    def get_battery_info(self):
        """دریافت اطلاعات باتری"""
        try:
            success, output = self.run_command("shell dumpsys battery")
            if success:
                battery_info = {}
                for line in output.split('\n'):
                    if 'level' in line.lower():
                        battery_info['level'] = line.split(':')[1].strip()
                    elif 'scale' in line.lower():
                        battery_info['scale'] = line.split(':')[1].strip()
                    elif 'status' in line.lower():
                        battery_info['status'] = line.split(':')[1].strip()
                
                self.logger.debug("Battery info retrieved")
                return battery_info
            else:
                return {"error": "Failed to get battery info"}
                
        except Exception as e:
            self.logger.error(f"Error getting battery info: {e}")
            return {"error": str(e)}

    def get_device_info(self):
        """دریافت اطلاعات دستگاه"""
        try:
            info = {}
            
            # مدل دستگاه
            success, output = self.run_command("shell getprop ro.product.model")
            if success:
                info['model'] = output.strip()
            
            # نسخه اندروید
            success, output = self.run_command("shell getprop ro.build.version.release")
            if success:
                info['android_version'] = output.strip()
            
            # سازنده
            success, output = self.run_command("shell getprop ro.product.manufacturer")
            if success:
                info['manufacturer'] = output.strip()
            
            # سریال
            success, output = self.run_command("shell getprop ro.serialno")
            if success:
                info['serial'] = output.strip()
            
            self.logger.debug("Device info retrieved")
            return info
            
        except Exception as e:
            self.logger.error(f"Error getting device info: {e}")
            return {"error": str(e)}

    def take_screenshot(self, filename=None):
        """گرفتن اسکرین‌شات"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            remote_path = f"/sdcard/{filename}"
            local_path = f"/tmp/{filename}"
            
            # گرفتن اسکرین‌شات
            success, message = self.run_command(f"shell screencap -p {remote_path}")
            if not success:
                self.logger.error(f"Failed to take screenshot: {message}")
                return None
            
            # انتقال به سرور
            success, message = self.run_command(f"pull {remote_path} {local_path}", timeout=20)
            if success:
                self.logger.info(f"Screenshot saved: {local_path}")
                return local_path
            else:
                self.logger.error(f"Failed to transfer screenshot: {message}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return None

    def cleanup(self):
        """تمیزکاری منابع"""
        try:
            self.monitor_running = False
            if self.connection_monitor_thread and self.connection_monitor_thread.is_alive():
                self.connection_monitor_thread.join(timeout=2.0)
            
            self.logger.info("Phone Controller cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """دستکتور برای تمیزکاری خودکار"""
        self.cleanup()

# تست مستقل
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("📱 Testing Phone Controller...")
    
    try:
        phone = PhoneController()
        
        # صبر برای اتصال
        print("1. Waiting for connection...")
        for i in range(30):  # 30 ثانیه منتظر بمان
            if phone.check_connection():
                print("✅ Phone connected!")
                break
            time.sleep(1)
        else:
            print("❌ No phone connected")
            exit(1)
        
        # تست اطلاعات دستگاه
        print("2. Testing device info...")
        device_info = phone.get_device_info()
        print(f"Device Info: {device_info}")
        
        # تست اطلاعات باتری
        print("3. Testing battery info...")
        battery_info = phone.get_battery_info()
        print(f"Battery Info: {battery_info}")
        
        # تست کنترل صفحه
        print("4. Testing screen control...")
        phone.wake_screen()
        time.sleep(2)
        
        # تست کنترل صدا
        print("5. Testing volume control...")
        phone.set_volume(50)
        time.sleep(1)
        phone.set_max_volume()
        time.sleep(1)
        phone.set_volume(30)
        
        # تست ویبره
        print("6. Testing vibration...")
        phone.start_vibration()
        time.sleep(2)
        phone.stop_vibration()
        
        # تست کنترل مدیا
        print("7. Testing media control...")
        phone.stop_all_media()
        
        # تست آلارم
        print("8. Testing alarm...")
        phone.play_alarm()
        time.sleep(3)
        phone.stop_all_media()
        
        print("✅ Phone Controller test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        phone.cleanup()