# pyinstaller --onefile wallapop_monitor.py

import requests
import time
import webbrowser
import os
import pprint
import ctypes
from uuid import uuid4
import urllib.parse
# Settings
BASE_FILENAME = "wallapop_python"
TOKEN_FILENAME = f"{BASE_FILENAME}_token.txt"
SAVED_SEARCH_URL = "https://api.wallapop.com/api/v3/searchalerts/savedsearch/"

HEADERS_TEMPLATE = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 OPR/114.0.0.0",
    "Host": "api.wallapop.com",
    "Origin": "https://pt.wallapop.com",
    "Referer": "https://pt.wallapop.com/",
    "x-appversion": "83540",
    "x-deviceid": "01f7ed0d-4b82-44bb-ba34-04e2ff3cb409",
    "x-deviceos": "0",
    "Connection": "keep-alive",
}

# Track last seen items
last_items = {}

def get_file_path(filename):
    base_dir = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base_dir, filename)

def load_token():
    token_path = get_file_path(TOKEN_FILENAME)
    if os.path.exists(token_path) and os.path.getsize(token_path) > 0:
        with open(token_path, "r") as file:
            return file.read().strip()
    return None

def save_token(token):
    token_path = get_file_path(TOKEN_FILENAME)
    with open(token_path, "w") as file:
        file.write(token)

def update_headers_with_token(headers, token):
    headers["Authorization"] = f"Bearer {token}"

def show_message(title, text):
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)  # MB_ICONINFORMATION


def ask_token():
    """
    Opens Notepad so the user can paste their full Wallapop token.
    This avoids InputBox limits and supports long tokens.
    """
    import subprocess
    import tempfile

    instructions = (
        "Paste your Wallapop token below, replacing this line.\n\n"
        "Example:\n"
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...\n\n"
        "👉 After pasting your token, press Ctrl+S to save, then close the Notepad window.\n"
    )

    # Create temp file with instructions
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as f:
        f.write(instructions)
        file_path = f.name

    # Open Notepad
    subprocess.run(["notepad.exe", file_path])

    # Read final token
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    os.remove(file_path)

    # Extract first valid (non-empty, non-comment) line
    token = ""
    for line in lines:
        line = line.strip()
        if line and not line.startswith("Paste your") and not line.startswith("Example:") and not line.startswith("👉"):
            token = line
            break

    print(f"[DEBUG] Token from notepad: '{token}'")
    return token



def open_in_browser(query_params):
    query_string = "&".join([
        f"{key}={','.join(map(str, value))}" if isinstance(value, list) else f"{key}={value}"
        for key, value in query_params.items() if value
    ])
    search_url = f"https://pt.wallapop.com/app/search?{query_string}"
    print(f"Opening search: {search_url}")
    webbrowser.open_new_tab(search_url)

def check_for_items(headers):
    global last_items
    try:
        print("Getting saved alerts...")
        response = requests.get(SAVED_SEARCH_URL, headers=headers, timeout=15)

        if response.status_code in (400, 401):
            print("Invalid or expired token!")
            return False

        response.raise_for_status()
        saved_alerts = response.json()

        for alert in saved_alerts:
            query = alert.get("query", {})
            base_url = "https://api.wallapop.com/api/v3/search"

            params = "&".join([
                f"{key}={','.join(map(str, value))}" if isinstance(value, list) else f"{key}={value}"
                for key, value in query.items() if value
            ])


            keywords = query.get("keywords")
            if not keywords:
                continue

            search_id = str(uuid4())
            full_url = f"https://api.wallapop.com/api/v3/search?source=search_box&keywords={urllib.parse.quote_plus(keywords)}&search_id={search_id}"
            print(f"Requesting URL: {full_url}")

 
            response = requests.get(full_url, headers=headers, timeout=15)
            if response.status_code == 401:
                print("Invalid token!")
                return False

            response.raise_for_status()
            data = response.json()
            items = data.get("data", {}).get("section", {}).get("payload", {}).get("items", [])

            if items:
                last_item = items[0]
                item_id = last_item.get("id")

                if full_url in last_items and last_items[full_url] != item_id:
                    print(f"🔔 New item found for '{query.get('keywords')}'!")
                    pprint.pprint(last_item)
                    last_items[full_url] = item_id
                    open_in_browser(query)
                else:
                    print(f"✅ First check for '{query.get('keywords')}'.")
                    last_items[full_url] = item_id

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Something went wrong: {e}")
    return True

def main():
    global last_items
    print("Starting watch...")

    token = load_token()
    if not token:
        token = ask_token()
        if not token:
            show_message("Token missing", "No token entered. Closing app.")
            return
        save_token(token)

    headers = HEADERS_TEMPLATE.copy()
    update_headers_with_token(headers, token)

    while True:
        if not check_for_items(headers):
            token = ask_token()
            if not token:
                show_message("Token missing", "No token entered. Closing app.")
                return
            save_token(token)
            update_headers_with_token(headers, token)
        time.sleep(10)

if __name__ == "__main__":
    main()
