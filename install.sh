#!/bin/bash

echo "🔧 Installing Study Assistant Web..."

# به روز رسانی سیستم
sudo apt update && sudo apt upgrade -y

# نصب پیش‌نیازها
sudo apt install python3 python3-pip python3-venv adb -y
sudo apt install libopencv-dev libatlas-base-dev -y

# ایجاد محیط مجازی
python3 -m venv web_assistant
source web_assistant/bin/activate

# نصب کتابخانه‌های پایتون
pip install -r requirements.txt

# دادن مجوز اجرا
chmod +x run.sh

echo "✅ Installation completed!"
echo "🚀 Run: ./run.sh to start the application"