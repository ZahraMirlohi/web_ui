# gpio_controller.py
import logging
import time
import threading
from config.settings import LIGHT_PIN, PWM_FREQUENCY

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    print(⚠️ RPi.GPIO not available - running in simulation mode")

class GPIOController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.light_pin = LIGHT_PIN
        self.pwm_frequency = PWM_FREQUENCY
        self.current_brightness = 0
        self.is_light_on = False
        self.pwm = None
        self.auto_off_timer = None
        
        self.setup_gpio()
        self.logger.info("GPIO Controller initialized")

    def setup_gpio(self):
        """تنظیم GPIO"""
        try:
            if HAS_GPIO:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.light_pin, GPIO.OUT)
                self.pwm = GPIO.PWM(self.light_pin, self.pwm_frequency)
                self.pwm.start(0)  # شروع با روشنایی 0%
                self.logger.info("Real GPIO setup completed")
            else:
                self.logger.info("GPIO simulation mode activated")
                
        except Exception as e:
            self.logger.error(f"Error setting up GPIO: {e}")
            raise

    def light_on(self, brightness=100):
        """روشن کردن چراغ با روشنایی مشخص"""
        try:
            if not 0 <= brightness <= 100:
                raise ValueError("Brightness must be between 0 and 100")
            
            self.current_brightness = brightness
            self.is_light_on = True
            
            if HAS_GPIO and self.pwm:
                self.pwm.ChangeDutyCycle(brightness)
                self.logger.info(f"Light turned ON with {brightness}% brightness")
            else:
                self.logger.info(f"Simulation: Light ON with {brightness}% brightness")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error turning light on: {e}")
            return False

    def light_off(self):
        """خاموش کردن چراغ"""
        try:
            self.is_light_on = False
            self.current_brightness = 0
            
            if HAS_GPIO and self.pwm:
                self.pwm.ChangeDutyCycle(0)
                self.logger.info("Light turned OFF")
            else:
                self.logger.info("Simulation: Light OFF")
            
            # لغو تایمر خاموش‌کن خودکار
            if self.auto_off_timer:
                self.auto_off_timer.cancel()
                self.auto_off_timer = None
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error turning light off: {e}")
            return False

    def set_brightness(self, brightness):
        """تنظیم روشنایی چراغ"""
        try:
            if not 0 <= brightness <= 100:
                raise ValueError("Brightness must be between 0 and 100")
            
            self.current_brightness = brightness
            
            if brightness > 0:
                self.is_light_on = True
                if HAS_GPIO and self.pwm:
                    self.pwm.ChangeDutyCycle(brightness)
                self.logger.info(f"Brightness set to {brightness}%")
            else:
                self.light_off()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting brightness: {e}")
            return False

    def get_light_status(self):
        """دریافت وضعیت چراغ"""
        return {
            "is_on": self.is_light_on,
            "brightness": self.current_brightness,
            "pin": self.light_pin,
            "mode": "REAL" if HAS_GPIO else "SIMULATION"
        }

    def toggle_light(self):
        """تغییر وضعیت چراغ"""
        if self.is_light_on:
            return self.light_off()
        else:
            return self.light_on(self.current_brightness or 50)

    def fade_in(self, duration=3, target_brightness=100):
        """افزایش تدریجی روشنایی"""
        def fade_thread():
            try:
                steps = int(duration * 10)  # 10 steps per second
                step_delay = duration / steps
                
                for i in range(steps + 1):
                    brightness = int((i / steps) * target_brightness)
                    self.set_brightness(brightness)
                    time.sleep(step_delay)
                    
                self.logger.info(f"Fade in completed to {target_brightness}%")
            except Exception as e:
                self.logger.error(f"Error in fade in: {e}")

        threading.Thread(target=fade_thread, daemon=True).start()
        return True

    def fade_out(self, duration=3):
        """کاهش تدریجی روشنایی"""
        def fade_thread():
            try:
                start_brightness = self.current_brightness
                steps = int(duration * 10)  # 10 steps per second
                step_delay = duration / steps
                
                for i in range(steps + 1):
                    brightness = int(start_brightness * (1 - i / steps))
                    self.set_brightness(brightness)
                    time.sleep(step_delay)
                    
                self.light_off()
                self.logger.info("Fade out completed")
            except Exception as e:
                self.logger.error(f"Error in fade out: {e}")

        threading.Thread(target=fade_thread, daemon=True).start()
        return True

    def blink(self, times=3, interval=0.5, brightness=100):
        """چشمک زدن چراغ"""
        def blink_thread():
            try:
                original_brightness = self.current_brightness
                original_state = self.is_light_on
                
                for i in range(times):
                    self.set_brightness(brightness)
                    time.sleep(interval)
                    self.set_brightness(0)
                    if i < times - 1:  # برای دفعه آخر صبر نکن
                        time.sleep(interval)
                
                # بازگشت به حالت قبلی
                if original_state:
                    self.set_brightness(original_brightness)
                else:
                    self.light_off()
                    
                self.logger.info(f"Blinked {times} times")
            except Exception as e:
                self.logger.error(f"Error in blinking: {e}")

        threading.Thread(target=blink_thread, daemon=True).start()
        return True

    def set_auto_off(self, minutes):
        """تنظیم خاموش‌کن خودکار"""
        try:
            # لغو تایمر قبلی اگر وجود دارد
            if self.auto_off_timer:
                self.auto_off_timer.cancel()

            def auto_off():
                self.light_off()
                self.logger.info(f"Auto turn off after {minutes} minutes")

            self.auto_off_timer = threading.Timer(minutes * 60, auto_off)
            self.auto_off_timer.start()
            
            self.logger.info(f"Auto off timer set for {minutes} minutes")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting auto off: {e}")
            return False

    def get_power_consumption(self):
        """محاسبه مصرف برق (تخمینی)"""
        # فرض: چراغ 5 وات در حداکثر روشنایی
        max_wattage = 5
        consumption = (self.current_brightness / 100) * max_wattage
        return {
            "current_watts": consumption,
            "max_watts": max_wattage,
            "efficiency": f"{100 - self.current_brightness}% energy saved"
        }

    def set_light_mode(self, mode, **kwargs):
        """تنظیم حالت‌های مختلف چراغ"""
        modes = {
            "reading": {"brightness": 75, "description": "حالت مطالعه"},
            "night": {"brightness": 25, "description": "حالت مطالعه شب"},
            "bright": {"brightness": 100, "description": "حداکثر روشنایی"},
            "eco": {"brightness": 50, "description": "حالت اقتصادی"}
        }
        
        if mode not in modes:
            raise ValueError(f"Invalid mode. Available modes: {list(modes.keys())}")
        
        config = modes[mode]
        brightness = kwargs.get('brightness', config['brightness'])
        
        success = self.set_brightness(brightness)
        if success:
            self.logger.info(f"Light mode set to '{mode}' ({config['description']})")
        
        return success

    def cleanup(self):
        """تمیزکاری و آزادسازی منابع"""
        try:
            self.light_off()
            
            if self.auto_off_timer:
                self.auto_off_timer.cancel()
            
            if HAS_GPIO and self.pwm:
                self.pwm.stop()
                GPIO.cleanup()
                
            self.logger.info("GPIO Controller cleaned up")
            
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
    
    print("🔧 Testing GPIO Controller...")
    
    try:
        gpio = GPIOController()
        
        # تست روشن/خاموش
        print("1. Testing ON/OFF...")
        gpio.light_on(50)
        time.sleep(2)
        gpio.light_off()
        time.sleep(1)
        
        # تست تنظیم روشنایی
        print("2. Testing brightness control...")
        for brightness in [25, 50, 75, 100]:
            gpio.set_brightness(brightness)
            time.sleep(1)
        
        # تست حالت‌ها
        print("3. Testing light modes...")
        gpio.set_light_mode("reading")
        time.sleep(2)
        gpio.set_light_mode("night")
        time.sleep(2)
        gpio.set_light_mode("eco")
        time.sleep(2)
        
        # تست چشمک زدن
        print("4. Testing blink...")
        gpio.blink(times=3, interval=0.3)
        time.sleep(3)
        
        # تست وضعیت
        print("5. Testing status...")
        status = gpio.get_light_status()
        print(f"Light Status: {status}")
        
        power = gpio.get_power_consumption()
        print(f"Power Consumption: {power}")
        
        # تست خاموش‌کن خودکار (کوتاه)
        print("6. Testing auto-off (10 seconds)...")
        gpio.light_on(75)
        gpio.set_auto_off(0.17)  # 10 ثانیه
        
        time.sleep(12)  # صبر برای فعال شدن خاموش‌کن خودکار
        
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        gpio.cleanup()