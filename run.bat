@echo off
chcp 65001 > nul
echo ============================================
echo   Bot Sambung Kata KBBI - Telegram Bot
echo ============================================
echo.
if not exist ".env" (
    echo [ERROR] File .env tidak ditemukan!
    echo Salin .env.example menjadi .env lalu isi BOT_TOKEN kamu.
    pause
    exit /b 1
)
echo [INFO] Menjalankan bot...
python -X utf8 bot.py
pause
