# alarm_manager.py
import threading
import time
from datetime import datetime, timedelta
import subprocess
import os
import logging
from phone.controller import PhoneController

class AlarmManager:
    def __init__(self, root_app=None, status_callback=None):
        self.alarm_thread = None
        self.active_alarm = None
        self.status_callback = status_callback
        self.is_running = False
        self.root_app = root_app
        self.phone_controller = PhoneController()
        self.alarm_sound_playing = False
        
        # تنظیمات logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_iran_time(self):
        """دریافت زمان فعلی ایران (UTC+3:30)"""
        try:
            now_utc = datetime.utcnow()
            
            # تبدیل به وقت ایران (UTC+3:30)
            hour_iran = (now_utc.hour + 3) % 24
            minute_iran = (now_utc.minute + 30) % 60
            second_iran = now_utc.second
            
            # اگر دقیقه از 60 بیشتر شد، ساعت رو افزایش بده
            if now_utc.minute + 30 >= 60:
                hour_iran = (hour_iran + 1) % 24
            
            # ایجاد datetime ایران
            iran_time = now_utc.replace(
                hour=hour_iran,
                minute=minute_iran,
                second=second_iran
            )
            
            return iran_time
            
        except Exception as e:
            self.logger.error(f"Error getting Iran time: {e}")
            return datetime.utcnow()

    def set_alarm(self, hour, minute):
        """تنظیم آلارم جدید بر اساس ساعت ایران"""
        try:
            # متوقف کردن آلارم قبلی اگر وجود دارد
            self.stop_alarm()

            # زمان فعلی ایران
            now_iran = self.get_iran_time()
            
            # ایجاد datetime آلارم برای امروز
            alarm_datetime = now_iran.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # اگر زمان آلارم قبل از زمان حال است، برای فردا تنظیم شود
            if alarm_datetime <= now_iran:
                alarm_datetime += timedelta(days=1)
            
            self.active_alarm = alarm_datetime
            
            # شروع thread برای چک کردن آلارم
            self.is_running = True
            self.alarm_thread = threading.Thread(target=self._alarm_checker, daemon=True)
            self.alarm_thread.start()
            
            alarm_time_str = alarm_datetime.strftime('%H:%M')
            alarm_date_str = alarm_datetime.strftime('%Y/%m/%d')
            message = f"⏰ آلارم تنظیم شد برای {alarm_time_str} ({alarm_date_str})"
            
            if self.status_callback:
                self.status_callback(message)
            
            self.logger.info(f"Alarm set for {alarm_datetime}")
            return True
            
        except Exception as e:
            error_msg = f"❌ خطا در تنظیم آلارم: {str(e)}"
            if self.status_callback:
                self.status_callback(error_msg)
            self.logger.error(f"Error setting alarm: {e}")
            return False

    def _alarm_checker(self):
        """چک کردن زمان آلارم بر اساس زمان ایران"""
        self.logger.info("Alarm checker started")
        
        while self.is_running and self.active_alarm:
            try:
                now_iran = self.get_iran_time()
                
                # بررسی آیا زمان آلارم رسیده
                if now_iran >= self.active_alarm:
                    self.logger.info("Alarm time reached! Triggering alarm...")
                    self._trigger_alarm()
                    break
                
                # نمایش زمان باقی مانده هر 30 ثانیه
                if now_iran.second % 30 == 0:
                    time_left = self.active_alarm - now_iran
                    minutes_left = int(time_left.total_seconds() / 60)
                    if minutes_left <= 5:  # فقط برای 5 دقیقه آخر
                        self.logger.info(f"Alarm in {minutes_left} minutes")
                
                # چک کردن هر ثانیه
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in alarm checker: {e}")
                break
        
        self.logger.info("Alarm checker stopped")

    def _trigger_alarm(self):
        """فعال کردن آلارم"""
        try:
            self.logger.info("Starting alarm sequence...")
            
            # 1. روشن کردن صفحه گوشی
            self._wake_phone_screen()
            
            # 2. تنظیم حداکثر صدا
            self._set_max_volume()
            
            # 3. پخش صدای آلارم
            self._play_alarm_sound()
            
            # 4. فعال کردن ویبره
            self._start_vibration()
            
            # 5. نمایش پیام
            message = "🔔 زمان مطالعه به پایان رسید! آلارم فعال شد."
            if self.status_callback:
                self.status_callback(message)
            
            self.logger.info("Alarm triggered successfully")
            
            # ایجاد پنجره هشدار (در thread اصلی GUI)
            if self.root_app:
                try:
                    from alarm_alert_window import AlarmAlertWindow
                    self.root_app.after(0, self._show_alarm_alert)
                except ImportError as e:
                    self.logger.warning(f"Could not import AlarmAlertWindow: {e}")
                    
        except Exception as e:
            error_msg = f"❌ خطا در فعال کردن آلارم: {str(e)}"
            if self.status_callback:
                self.status_callback(error_msg)
            self.logger.error(f"Error triggering alarm: {e}")

    def _wake_phone_screen(self):
        """روشن کردن صفحه گوشی"""
        try:
            self.phone_controller.wake_screen()
            self.logger.info("Phone screen awakened")
        except Exception as e:
            self.logger.error(f"Error waking phone screen: {e}")

    def _set_max_volume(self):
        """تنظیم حداکثر صدا"""
        try:
            self.phone_controller.set_max_volume()
            self.logger.info("Volume set to maximum")
        except Exception as e:
            self.logger.error(f"Error setting max volume: {e}")

    def _play_alarm_sound(self):
        """پخش صدای آلارم"""
        try:
            # پخش آلارم از طریق گوشی
            success = self.phone_controller.play_alarm()
            if success:
                self.alarm_sound_playing = True
                self.logger.info("Alarm sound started playing")
            else:
                self.logger.warning("Could not play alarm sound through phone")
                
                # روش جایگزین: استفاده از آلارم سیستم
                self._play_system_alarm()
                
        except Exception as e:
            self.logger.error(f"Error playing alarm sound: {e}")
            self._play_system_alarm()

    def _play_system_alarm(self):
        """پخش آلارم سیستم به عنوان جایگزین"""
        try:
            # استفاده از adb برای پخش آلارم سیستم
            subprocess.run([
                'adb', 'shell', 'am', 'start',
                '-a', 'android.intent.action.VIEW',
                '-d', 'file:///system/media/audio/alarms/Alarm_Beep_03.ogg'
            ], timeout=10, check=False)
            
            self.logger.info("System alarm triggered")
        except Exception as e:
            self.logger.error(f"Error playing system alarm: {e}")

    def _start_vibration(self):
        """شروع ویبره"""
        try:
            self.phone_controller.start_vibration()
            self.logger.info("Vibration started")
        except Exception as e:
            self.logger.error(f"Error starting vibration: {e}")

    def _show_alarm_alert(self):
        """نمایش پنجره هشدار آلارم"""
        try:
            from alarm_alert_window import AlarmAlertWindow
            self.alert_window = AlarmAlertWindow(self.root_app)
            self.logger.info("Alarm alert window shown")
        except Exception as e:
            self.logger.error(f"Error showing alarm alert: {e}")

    def stop_alarm(self):
        """متوقف کردن آلارم"""
        self.logger.info("Stopping alarm...")
        
        self.is_running = False
        self.active_alarm = None
        
        try:
            # توقف صدا
            self.phone_controller.stop_all_media()
            self.alarm_sound_playing = False
            
            # توقف ویبره
            self.phone_controller.stop_vibration()
            
            # خاموش کردن صفحه (اختیاری)
            # self.phone_controller.turn_screen_off()
            
            self.logger.info("Alarm stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping alarm: {e}")
        
        if self.status_callback:
            self.status_callback("⏹️ آلارم متوقف شد")

    def get_alarm_status(self):
        """دریافت وضعیت آلارم"""
        if self.active_alarm:
            time_str = self.active_alarm.strftime('%H:%M')
            date_str = self.active_alarm.strftime('%Y/%m/%d')
            return f"⏰ آلارم فعال: {time_str} ({date_str})"
        return "⏰ هیچ آلارمی فعال نیست"

    def get_time_until_alarm(self):
        """دریافت زمان باقی مانده تا آلارم"""
        if not self.active_alarm:
            return None
            
        now_iran = self.get_iran_time()
        time_left = self.active_alarm - now_iran
        
        if time_left.total_seconds() <= 0:
            return "آلارم فعال شده"
        
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours} ساعت و {minutes} دقیقه"
        else:
            return f"{minutes} دقیقه"

    def set_quick_alarm(self, minutes_from_now):
        """تنظیم آلارم سریع برای دقیقه‌های آینده"""
        try:
            now_iran = self.get_iran_time()
            alarm_time = now_iran + timedelta(minutes=minutes_from_now)
            
            return self.set_alarm(alarm_time.hour, alarm_time.minute)
            
        except Exception as e:
            error_msg = f"❌ خطا در تنظیم آلارم سریع: {str(e)}"
            if self.status_callback:
                self.status_callback(error_msg)
            self.logger.error(f"Error setting quick alarm: {e}")
            return False

    def is_alarm_active(self):
        """بررسی فعال بودن آلارم"""
        return self.active_alarm is not None and self.is_running

    def cleanup(self):
        """تمیزکاری منابع"""
        self.stop_alarm()
        if self.alarm_thread and self.alarm_thread.is_alive():
            self.alarm_thread.join(timeout=1.0)

# تست مستقل
if __name__ == "__main__":
    def test_callback(message):
        print(f"Status: {message}")
    
    alarm_manager = AlarmManager(status_callback=test_callback)
    
    # تست تنظیم آلارم برای 2 دقیقه دیگر
    now = alarm_manager.get_iran_time()
    test_time = now + timedelta(minutes=2)
    
    print(f"Setting alarm for {test_time.strftime('%H:%M')}")
    alarm_manager.set_alarm(test_time.hour, test_time.minute)
    
    try:
        # اجرا برای 5 دقیقه
        time.sleep(300)
    except KeyboardInterrupt:
        print("\nStopping alarm manager...")
        alarm_manager.cleanup()