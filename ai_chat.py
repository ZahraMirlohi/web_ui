# ai_chat.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import requests
import json
import os
import re
import time
import logging
from config.settings import OPENROUTER_API_KEY, OPENROUTER_API_URL

class ConfigManager:
    @staticmethod
    def get_api_key():
        """دریافت API Key از تنظیمات"""
        try:
            api_key = OPENROUTER_API_KEY
            if api_key and "YOUR_API_KEY" not in api_key and len(api_key) > 20:
                logging.info("API Key found in settings")
                return api_key
            else:
                logging.error("Invalid API Key in settings")
                return None
        except Exception as e:
            logging.error(f"Error reading API key: {e}")
            return None

class ModelManager:
    def __init__(self):
        self.models = [
            {"name": "google/gemini-2.0-flash-exp:free", "priority": 10, "max_tokens": 4000, "failed": False},
            {"name": "google/gemini-2.0-flash:free", "priority": 9, "max_tokens": 4000, "failed": False},
            {"name": "meta-llama/llama-3.1-8b-instruct:free", "priority": 8, "max_tokens": 4000, "failed": False},
            {"name": "mistralai/mistral-7b-instruct:free", "priority": 7, "max_tokens": 4000, "failed": False},
            {"name": "qwen/qwen-2.5-7b-instruct:free", "priority": 6, "max_tokens": 4000, "failed": False},
            {"name": "microsoft/wizardlm-2-8x22b:free", "priority": 5, "max_tokens": 2000, "failed": False},
            {"name": "huggingfaceh4/zephyr-7b-beta:free", "priority": 4, "max_tokens": 2000, "failed": False},
        ]
        self.logger = logging.getLogger(__name__)

    def get_next_model(self):
        """دریافت مدل بعدی بر اساس اولویت"""
        available_models = [m for m in self.models if not m["failed"]]
        available_models.sort(key=lambda x: x["priority"], reverse=True)
        
        if available_models:
            self.logger.info(f"Selected model: {available_models[0]['name']}")
            return available_models[0]
        
        # اگر همه مدل‌ها شکست خوردند، یک مدل را ریست می‌کنیم
        self.reset_failed_models()
        available_models = [m for m in self.models if not m["failed"]]
        if available_models:
            return available_models[0]
        
        return self.models[0]

    def mark_model_failed(self, model_name):
        """علامت‌گذاری مدل به عنوان شکست خورده"""
        for model in self.models:
            if model["name"] == model_name:
                model["failed"] = True
                self.logger.warning(f"Model marked as failed: {model_name}")
                break

    def reset_failed_models(self):
        """ریست کردن وضعیت شکست مدل‌ها"""
        for model in self.models:
            model["failed"] = False
        self.logger.info("All models reset")

class AIChat:
    def __init__(self, status_callback=None):
        self.messages = []
        self.model_manager = ModelManager()
        self.status_callback = status_callback
        self.logger = logging.getLogger(__name__)
        
        # اضافه کردن پیام سیستم
        system_message = {
            "role": "system",
            "content": """شما یک دستیار هوش مصنوعی مفید برای کمک به دانش‌آموزان و دانشجویان هستید. 
لطفاً به زبان فارسی پاسخ دهید و پاسخ‌های دقیق، آموزشی و مفیدی ارائه دهید.

دستورالعمل‌ها:
1. همیشه به زبان فارسی پاسخ دهید
2. پاسخ‌ها باید آموزشی و دقیق باشند
3. برای مسائل پیچیده، راه حل مرحله به مرحله ارائه دهید
4. اگر سوال مبهم است، برای شفاف‌سازی سوال بپرسید
5. از اصطلاحات فنی به طور مناسب استفاده کنید
6. در صورت لزوم مثال بزنید"""
        }
        self.messages.append(system_message)

    def send_message(self, user_message):
        """ارسال پیام به هوش مصنوعی و دریافت پاسخ"""
        try:
            self.logger.info("Sending message to AI")
            
            if self.status_callback:
                self.status_callback("🤖 در حال پردازش...")

            api_key = ConfigManager.get_api_key()
            if not api_key:
                error_msg = "خطا: API Key یافت نشد"
                self.logger.error(error_msg)
                if self.status_callback:
                    self.status_callback("❌ خطا در API Key")
                return error_msg

            # اضافه کردن پیام کاربر به تاریخچه
            self.messages.append({"role": "user", "content": user_message})

            # امتحان مدل‌های مختلف
            max_attempts = 5
            attempt = 0
            success = False
            response_text = ""

            while attempt < max_attempts and not success:
                model = self.model_manager.get_next_model()
                self.logger.info(f"Attempt {attempt + 1}/{max_attempts} with model: {model['name']}")
                
                try:
                    response_text = self._try_model(api_key, model, user_message)
                    if response_text:
                        success = True
                        self.logger.info(f"Success with model: {model['name']}")
                    else:
                        self.model_manager.mark_model_failed(model["name"])
                    
                except Exception as e:
                    self.logger.error(f"Error with model {model['name']}: {e}")
                    self.model_manager.mark_model_failed(model["name"])
                
                attempt += 1

            if not success:
                error_msg = "⚠️ همه مدل‌ها شکست خوردند. لطفاً اتصال اینترنت را بررسی کنید."
                self.logger.error(error_msg)
                if self.status_callback:
                    self.status_callback("❌ خطا در ارتباط")
                return error_msg

            # اضافه کردن پاسخ به تاریخچه
            self.messages.append({"role": "assistant", "content": response_text})

            if self.status_callback:
                self.status_callback("✅ پاسخ دریافت شد")

            return response_text

        except Exception as e:
            error_msg = f"❌ خطای سیستمی: {str(e)}"
            self.logger.error(f"System error: {e}")
            if self.status_callback:
                self.status_callback("❌ خطای سیستمی")
            return error_msg

    def _try_model(self, api_key, model, user_message):
        """امتحان کردن یک مدل خاص"""
        try:
            url = OPENROUTER_API_URL
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/study-assistant",
                "X-Title": "Study Assistant"
            }

            # استفاده از تاریخچه گفتگو (آخرین 6 پیام)
            recent_messages = self.messages[-6:] if len(self.messages) > 6 else self.messages

            data = {
                "model": model["name"],
                "messages": recent_messages,
                "temperature": 0.7,
                "max_tokens": model["max_tokens"],
                "top_p": 0.9,
                "stream": False
            }

            self.logger.debug(f"Sending request to model: {model['name']}")
            response = requests.post(url, headers=headers, json=data, timeout=45)
            
            if response.status_code == 200:
                result = response.json()
                ai_message = result['choices'][0]['message']['content']
                self.logger.info("AI response received successfully")
                return ai_message
            
            elif response.status_code == 400:
                self.logger.warning(f"Model {model['name']} returned 400: {response.text}")
                return None
                
            elif response.status_code == 404:
                self.logger.warning(f"Model {model['name']} not found (404)")
                return None
                
            else:
                self.logger.warning(f"Model {model['name']} returned {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout with model {model['name']}")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.warning(f"Connection error with model {model['name']}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error with model {model['name']}: {e}")
            return None

    def clear_conversation(self):
        """پاک کردن تاریخچه گفتگو"""
        self.messages = [
            {
                "role": "system",
                "content": "شما یک دستیار هوش مصنوعی مفید برای کمک به دانش‌آموزان و دانشجویان هستید. لطفاً به زبان فارسی پاسخ دهید و پاسخ‌های دقیق، آموزشی و مفیدی ارائه دهید."
            }
        ]
        self.logger.info("Conversation history cleared")
        if self.status_callback:
            self.status_callback("🗑️ تاریخچه پاک شد")

    def get_conversation_history(self):
        """دریافت تاریخچه گفتگو"""
        return self.messages.copy()

    def get_conversation_summary(self):
        """دریافت خلاصه گفتگو"""
        if len(self.messages) <= 1:  # فقط پیام سیستم
            return "هنوز گفتگویی صورت نگرفته است"
        
        user_messages = [msg["content"] for msg in self.messages if msg["role"] == "user"]
        if not user_messages:
            return "هنوز گفتگویی صورت نگرفته است"
        
        last_user_message = user_messages[-1]
        return f"آخرین سوال: {last_user_message[:100]}..." if len(last_user_message) > 100 else f"آخرین سوال: {last_user_message}"

    def save_conversation(self, filename=None):
        """ذخیره گفتگو در فایل"""
        try:
            if not filename:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"conversation_{timestamp}.json"
            
            conversation_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "messages": self.messages
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Conversation saved to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving conversation: {e}")
            return False

    def load_conversation(self, filename):
        """بارگذاری گفتگو از فایل"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)
            
            self.messages = conversation_data["messages"]
            self.logger.info(f"Conversation loaded from {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading conversation: {e}")
            return False

# تست مستقل
if __name__ == "__main__":
    # تنظیمات logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    def test_status_callback(message):
        print(f"Status: {message}")
    
    # تست کلاس AI Chat
    print("🤖 Testing AI Chat...")
    
    ai_chat = AIChat(status_callback=test_status_callback)
    
    # تست ارسال پیام
    test_messages = [
        "سلام! می‌توانی در مورد هوش مصنوعی توضیح بدهی؟",
        "مسئله ریاضی ساده: ۲ + ۲ چند می‌شود؟",
        "مفهوم فتوسنتز را توضیح بده"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Test {i} ---")
        print(f"You: {message}")
        
        response = ai_chat.send_message(message)
        print(f"AI: {response}")
        
        time.sleep(2)  # تاخیر بین تست‌ها
    
    # تست ذخیره و بارگذاری
    print("\n--- Testing Save/Load ---")
    ai_chat.save_conversation("test_conversation.json")
    print("Conversation saved")
    
    # پاک کردن و بارگذاری مجدد
    ai_chat.clear_conversation()
    print("Conversation cleared")
    
    ai_chat.load_conversation("test_conversation.json")
    print("Conversation loaded")
    
    print(f"Conversation summary: {ai_chat.get_conversation_summary()}")
    
    # پاک کردن فایل تست
    try:
        os.remove("test_conversation.json")
        print("Test file cleaned up")
    except:
        pass
    
    print("\n✅ AI Chat test completed!")