import os
import threading
import time
import io

import requests
import google.generativeai as genai
from flask import Flask
from PIL import Image

# ==========================================
# CONFIGURATION
# ==========================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not found.")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not found.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ==========================================
# FLASK APP (Needed for Render)
# ==========================================

app = Flask(__name__)

@app.route("/")
def home():
    return "ESP32 Gemini Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# TELEGRAM FUNCTIONS
# ==========================================

def get_updates(offset=None):
    url = f"{TELEGRAM_API_URL}/getUpdates"
    params = {"timeout": 100}

    if offset is not None:
        params["offset"] = offset

    try:
        response = requests.get(url, params=params, timeout=110)
        return response.json()
    except Exception as e:
        print(f"[ERROR] getUpdates: {e}")
        return None


def download_file(file_path):
    url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

    try:
        response = requests.get(url, timeout=30)
        return response.content
    except Exception as e:
        print(f"[ERROR] download_file: {e}")
        return None


def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[ERROR] send_message: {e}")


# ==========================================
# GEMINI
# ==========================================

def solve_math_problem(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))

        prompt = (
            "Analyze this image. "
            "Extract the question accurately. "
            "Solve it step by step. "
            "Return only the final answer."
        )

        response = model.generate_content([image, prompt])

        return response.text.strip()

    except Exception as e:
        print(f"[ERROR] Gemini: {e}")
        return "AI Error"


# ==========================================
# MAIN LOOP
# ==========================================

def main():

    print("Telegram-Gemini bridge started...")

    last_update_id = None

    while True:

        updates = get_updates(last_update_id)

        if updates and updates.get("ok"):

            for update in updates["result"]:

                last_update_id = update["update_id"] + 1

                if "message" not in update:
                    continue

                message = update["message"]

                if "photo" not in message:
                    continue

                chat_id = message["chat"]["id"]

                photo = message["photo"][-1]

                file_id = photo["file_id"]

                print("Image received")

                info = requests.get(
                    f"{TELEGRAM_API_URL}/getFile?file_id={file_id}"
                ).json()

                if not info.get("ok"):
                    continue

                file_path = info["result"]["file_path"]

                image = download_file(file_path)

                if image is None:
                    continue

                answer = solve_math_problem(image)

                send_message(chat_id, answer)

        time.sleep(1)


# ==========================================
# START
# ==========================================

if __name__ == "__main__":

    threading.Thread(target=main, daemon=True).start()

    run_web()
