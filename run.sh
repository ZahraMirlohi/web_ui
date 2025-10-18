#!/bin/bash

echo "🎯 Starting Study Assistant Web..."

# فعال کردن محیط مجازی
source web_assistant/bin/activate

# بررسی وجود پوشه‌های لازم
mkdir -p uploads/photos
mkdir -p uploads/music
mkdir -p logs

# راه‌اندازی سرور
python app.py

deactivate