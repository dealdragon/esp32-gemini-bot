import os
import io
import time
import threading

import requests
from openai import OpenAI
import base64
from flask import Flask
from PIL import Image

# =====================================
# CONFIG
# =====================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise Exception("Missing OPENROUTER_API_KEY")

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# =====================================
# FLASK
# =====================================

app = Flask(__name__)

@app.route("/")
def home():
    return "ESP32 Gemini Bot Running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =====================================
# TELEGRAM FUNCTIONS
# =====================================

def get_updates(offset=None):

    url = f"{TELEGRAM_API}/getUpdates"

    params = {
        "timeout": 100
    }

    if offset:
        params["offset"] = offset

    try:
        r = requests.get(url, params=params, timeout=120)
        return r.json()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("FULL ERROR:", repr(e))
        return f"OpenRouter Error:\n{type(e).__name__}: {repr(e)}"
        print(e)
        return None


def download_file(file_path):

    url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

    try:
        r = requests.get(url, timeout=30)
        return r.content
    except Exception as e:
        print(e)
        return None


def send_message(chat_id, text):

    url = f"{TELEGRAM_API}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    try:
        requests.post(url, json=payload, timeout=30)
    except Exception as e:
        print(e)


# =====================================
# GEMINI
# =====================================

def solve_question(image_bytes):
    try:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = """
Analyze the uploaded image carefully.

If it contains:
- Mathematics -> solve step by step.
- Physics -> answer with explanation.
- Chemistry -> answer with explanation.
- Biology -> answer with explanation.
- Electronics -> answer with explanation.
- Programming -> explain and solve.
- Artificial Intelligence / Machine Learning -> answer completely.
- Engineering questions -> answer completely.
- Descriptive questions -> answer in university exam format.
- Multiple questions -> answer every question.
- Handwritten questions -> read carefully.
- If any text is unreadable, clearly mention what cannot be read.

Presentation Rules:
- Use professional engineering university answer format.
- Show formulas before calculations.
- Show every calculation.
- Explain reasoning.
- Use headings.
- Use bullet points where needed.
- Keep answers neat.
- Keep answers concise but complete.
- Maximize marks in engineering examinations.
"""

        response = client.chat.completions.create(
            model="openrouter/auto",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"OpenRouter Error:\n{type(e).__name__}: {e}"
def main():

    print("Telegram-Gemini Bot Started")

    last_update_id = None

    while True:

        try:

            updates = get_updates(last_update_id)

            if updates and updates.get("ok"):

                for update in updates["result"]:

                    last_update_id = update["update_id"] + 1

                    if "message" not in update:
                        continue

                    message = update["message"]
# Ignore messages sent by bots
                     if message.get("from", {}).get("is_bot", False):
                       continue

# Ignore messages without a photo
                     if "photo" not in message:
                      continue

                    chat_id = message["chat"]["id"]

                    photo = message["photo"][-1]

                    file_id = photo["file_id"]

                    print("Image received")

                    info = requests.get(
                        f"{TELEGRAM_API}/getFile",
                        params={"file_id": file_id},
                        timeout=30
                    ).json()

                    if not info.get("ok"):
                        send_message(chat_id, "Could not download image.")
                        continue

                    file_path = info["result"]["file_path"]

                    image_bytes = download_file(file_path)

                    if image_bytes is None:
                        send_message(chat_id, "Image download failed.")
                        continue

                    answer = solve_question(image_bytes)

                    send_message(chat_id, answer)

        except Exception as e:
            print(f"[MAIN ERROR] {e}")

        time.sleep(1)


# =====================================
# START
# =====================================

if __name__ == "__main__":

    threading.Thread(
        target=main,
        daemon=True
    ).start()

    run_web()
