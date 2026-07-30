import os
import threading
from flask import Flask
import time
import requests
import google.generativeai as genai
from PIL import Image
import io

# ==========================================
# CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")"

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
# Using Gemini Flash for fast multimodal OCR and reasoning
model = genai.GenerativeModel('gemini-2.5-flash')

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def get_updates(offset=None):
    url = f"{TELEGRAM_API_URL}/getUpdates"
    params = {'timeout': 100, 'offset': offset}
    try:
        response = requests.get(url, params=params, timeout=110)
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch updates: {e}")
        return None

def download_file(file_path):
    url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    try:
        response = requests.get(url, timeout=30)
        return response.content
    except Exception as e:
        print(f"[ERROR] Failed to download file: {e}")
        return None

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[ERROR] Failed to send message: {e}")

def solve_math_problem(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        prompt = (
            "Analyze this image containing a math problem or equation. "
            "Extract the text/formula accurately, solve it step by step, "
            "and output ONLY the final answer clearly and concisely."
        )
        response = model.generate_content([image, prompt])
        return response.text.strip()
    except Exception as e:
        print(f"[ERROR] Gemini processing failed: {e}")
        return "AI Error: Could not solve."
        app = Flask(__name__)

@app.route("/")
def home():
    return "ESP32 Gemini Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def main():
    print("[INFO] Python Telegram-Gemini Bridge Started...")
    last_update_id = 0

    while True:
        updates = get_updates(offset=last_update_id + 1)
        if updates and 'result' in updates:
            for update in updates['result']:
                last_update_id = update['update_id']
                
                if 'message' in update and 'photo' in update['message']:
                    message = update['message']
                    chat_id = message['chat']['id']
                    
                    # Get the highest resolution photo available
                    photo = message['photo'][-1]
                    file_id = photo['file_id']
                    
                    print(f"[INFO] Received image from chat ID: {chat_id}")
                    
                    # Get file path from Telegram
                    file_info_url = f"{TELEGRAM_API_URL}/getFile?file_id={file_id}"
                    file_info_resp = requests.get(file_info_url).json()
                    
                    if file_info_resp.get('ok'):
                        file_path = file_info_resp['result']['file_path']
                        image_bytes = download_file(file_path)
                        
                        if image_bytes:
                            print("[INFO] Solving problem with Gemini AI...")
                            answer = solve_math_problem(image_bytes)
                            print(f"[INFO] Answer: {answer}")
                            
                            send_message(chat_id, answer)
        
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=main, daemon=True).start()
    run_web()
