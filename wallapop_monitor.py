# pyinstaller --onefile wallapop_monitor.py

import traceback
import requests
import time
import webbrowser
import os
from uuid import uuid4
import urllib.parse
import json
import logging
import platform

# Settings
STORAGE_PATH = "~"
BASE_FILENAME = "wallapop_python"
FILENAME_SAVED_HEADERS_TEMPLATE = f"{BASE_FILENAME}_headers_template.txt"
FILENAME_SAVED_LAST_ITEMS = f"{BASE_FILENAME}_last_items.json"
FILENAME_LOG = f"{BASE_FILENAME}.log"

OPTION_TIMEOUT_BETWEEN_GROUP_REQUESTS = 20  # seconds
OPTION_TIMEOUT_BETWEEN_SEARCH_REQUESTS = 1  # seconds

OPTION_OPEN_BROWSER = True # Open browser when new item is found

# URLs
URL_WALLAPOP_API_SAVED_SEARCH = "https://api.wallapop.com/api/v3/searchalerts/savedsearch/"
URL_WALLAPOP_API_SEARCH = "https://api.wallapop.com/api/v3/search"
URL_WALLAPOP_MAIN = "https://es.wallapop.com"
URL_WALLAPOP_MAIN_ITEM = f"{URL_WALLAPOP_MAIN}/item/"

# Setup logging
log = logging.getLogger(__name__)

# Track last seen items
last_items = {}

def get_file_path(filename):
    base_dir = (os.getenv("APPDATA") or os.path.expanduser("~")) if STORAGE_PATH == "~" else STORAGE_PATH
    return os.path.join(base_dir, filename)

def load_headers_template():
    saved_headers_template_file = get_file_path(FILENAME_SAVED_HEADERS_TEMPLATE)
    if os.path.exists(saved_headers_template_file) and os.path.getsize(saved_headers_template_file) > 0:
        with open(saved_headers_template_file, "rt", encoding="utf8") as file:
            return json.load(file)
    return None

def save_headers_template(header_template):
    saved_headers_template_file = get_file_path(FILENAME_SAVED_HEADERS_TEMPLATE)
    with open(saved_headers_template_file, "wt", encoding="utf8") as file:
        json.dump(header_template, file, indent=2, ensure_ascii=False)

def load_last_items():
    last_items_file = get_file_path(FILENAME_SAVED_LAST_ITEMS)
    if os.path.exists(last_items_file) and os.path.getsize(last_items_file) > 0:
        with open(last_items_file, "rt", encoding="utf8") as file:
            last_items = json.load(file)
    else:
        last_items = {}
    return last_items

def save_last_items(last_items):
    last_items_file = get_file_path(FILENAME_SAVED_LAST_ITEMS)
    with open(last_items_file, "wt", encoding="utf8") as file:
        json.dump(last_items, file, indent=2, ensure_ascii=False)

def update_headers_with_token(headers, token):
    headers["Authorization"] = f"Bearer {token}"

ctypes_imported = False
try:
    if platform.system() == "Windows":
        import ctypes
        ctypes_imported = True
except:
    pass

def has_console():
    if not ctypes_imported: return True
    # Returns True if the process has a console attached
    return ctypes.windll.kernel32.GetConsoleWindow() != 0

def show_message(title, text):
    if has_console():
        log.debug(f"{title}: {text}")
        return
    if ctypes_imported:
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)  # MB_ICONINFORMATION

def extract_headers_from_copied_fetch_request(fetch_request):
    """
    Extracts headers and token from a copied fetch(...) request.
    """
    fetch_data = None
    headers = None
    token = None

    # Extract first valid (non-empty, non-comment) line
    query_json_str = ""
    opened = False
    lines = fetch_request.splitlines() if isinstance(fetch_request, str) else (fetch_request if isinstance(fetch_request, list) else [])
    lines_str = "\n".join(lines).strip()
    if lines_str[:1] == '{' and lines_str[-1:] == '}':
        try:
            fetch_data = json.loads(lines_str)
            token = fetch_data.get("Authorization", "").replace("Bearer ", "")
            if not token or len(token) < 50:
                raise Exception("Authorization token is missing")
            return fetch_data, token
        except Exception as e:
            pass

    if not fetch_data:
        for line in lines:
            line = line.strip()
            if opened:
                query_json_str += line
            if not opened and line.startswith("fetch("):
                opened = True
                query_json_str = ""
            elif opened and line == "});":
                opened = False
                break
        if query_json_str:
            try:
                # Extract JSON part
                json_start = 0
                json_end = query_json_str.rindex("}") + 1
                json_str = query_json_str[json_start:json_end]
                if not json_str.startswith("{"):
                    json_str = "{" + json_str
                try:
                    fetch_data = json.loads(json_str)
                except Exception as e:
                    log.debug(f"Seems like the pasted data is not valid JSON: {json_str}")
                    raise Exception(f"Error decoding JSON: {e}")

            except Exception as e:
                raise Exception(f"Error parsing pasted data: {e}")

    if fetch_data:
        try:
            headers = fetch_data.get("headers", {})
            headers = {k.title(): v for k, v in headers.items()}
            token = headers.get("Authorization", "").replace("Bearer ", "")
            if fetch_data.get("method", "") == "OPTIONS":
                raise Exception("Request is an OPTIONS request, a GET request is needed.")
            if not token or len(token) < 50:
                raise Exception("Authorization token is missing")
            referrer = fetch_data.get("referrer", "")
            if referrer:
                headers['Referer'] = referrer
        except Exception as e:
            raise Exception(f"Error extracting headers/token: {e}")
        
    return headers, token


def ask_for_new_headers():
    """
    Opens Notepad so the user can paste the fetch(...) request.
    This function will parse the pasted data and extract the headers and token.
    """
    import subprocess
    import tempfile

    instructions = (
        "Open dev console and look for any GET request to: https://api.wallapop.com/api/v3/search\n"
        "Click 'Copy => Copy as fetch' in the context menu of this request.\n\n"
        "👉 After pasting your request, press Ctrl+S to save, then close the Notepad window.\n"
        "Example:\n" +
        """
        fetch("https://api.wallapop.com/api/v3/search/filters/model?source=side_bar_filters&category_id=24200&keywords=Lo+que+queres&order_by=price_low_to_high", {
          "headers": {
            "accept": "application/json, text/plain, */*",
            "authorization": "Bearer eyJhb...Op7A",
            "deviceos": "0",
            ...
            "x-appversion": "811730",
            "x-deviceid": "74c2d2d6-aade-4901-a70b-f5f7fd121537",
            "x-deviceos": "0"
          },
          "referrer": "https://es.wallapop.com/",
          "method": "GET",
        });
        """
    )

    # Create temp file with instructions
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as f:
        f.write(instructions)
        file_path = f.name

    # Open Notepad
    subprocess.run(["notepad.exe", file_path])

    # Read final token
    with open(file_path, "rt", encoding="utf-8") as f:
        fetch_request = f.read()

    os.remove(file_path)
    try:
        headers, token = extract_headers_from_copied_fetch_request(fetch_request)
    except Exception as e:
        log.error(f"Error extracting headers: {e}")
        return None

    log.debug(f"[DEBUG] Token from notepad: '{token}'")
    return headers


def open_item_in_browser(url):
    if OPTION_OPEN_BROWSER:
        log.debug(f"Opening item: {url}")
        webbrowser.open_new_tab(url)

g_custom_notification_fn = None
g_custom_notification_fn_error = None
try:
    import _custom_notifications
    g_custom_notification_fn = _custom_notifications.notify_new_item
    g_custom_notification_fn_error = _custom_notifications.notify_error
except:
    pass

def notify_new_item(item_title, item_price, item_url):
    log.info(f"New item found: '{item_title}' | {item_price} | {item_url}")
    if g_custom_notification_fn:
        g_custom_notification_fn(item_title, item_price, item_url)
    open_item_in_browser(item_url)

def notify_error(error_text):
    log.error(f"Error: {error_text}")
    if g_custom_notification_fn_error:
        g_custom_notification_fn_error(error_text)
    open_item_in_browser(item_url)

def check_for_items(headers):
    global last_items
    last_items_updated = False
    try:
        log.debug("Getting saved alerts...")
        response = requests.get(URL_WALLAPOP_API_SAVED_SEARCH, headers=headers, timeout=15)

        if response.status_code in (400, 401):
            log.error(f"Invalid or expired token! HTTP Code: {response.status_code}")
            return False

        response.raise_for_status()
        saved_alerts = response.json()
        unused_queries = set(last_items.keys())
        first_request = True

        for alert in saved_alerts:
            query = alert.get("query", {})

            exclude_params = set(['saved_search_id'])
            filter_params = [(key, value) for key, value in query.items() if value if key not in exclude_params]
            encoded_arguments = "&".join([
                f"{key}={urllib.parse.quote_plus(','.join(map(str, value)))}" if isinstance(value, list) else f"{key}={urllib.parse.quote_plus(str(value))}"
                for key, value in filter_params
            ])

            unused_queries -= set([encoded_arguments])
            keywords = query.get("keywords")
            if not keywords:
                continue

            full_url = f"{URL_WALLAPOP_API_SEARCH}?source=search_box&{encoded_arguments}"
            
            # Waiting between requests (to avoid being blocked)
            if not first_request:
                time.sleep(OPTION_TIMEOUT_BETWEEN_SEARCH_REQUESTS)
            else:
                first_request = False

            log.debug(f"Requesting URL: {full_url}")
 
            response = requests.get(full_url, headers=headers, timeout=15)
            if response.status_code == 401:
                log.debug("Invalid token!")
                return False

            response.raise_for_status()
            data = response.json()
            items = data.get("data", {}).get("section", {}).get("payload", {}).get("items", [])

            if items:
                #log.debug(json.dumps(items, indent=2))
                items_map = {item.get("id"): item for item in items}
                items_ids = list(items_map.keys())
                items_ids_diff = set(items_ids) - (set(last_items[encoded_arguments]) if (encoded_arguments in last_items) else set())

                if (encoded_arguments not in last_items):
                    last_items[encoded_arguments] = items_ids
                    log.debug(f"✅ First check for '{keywords}': Found {len(items_ids_diff)} items.")
                    last_items_updated = True
                elif items_ids_diff:
                    log.debug(f"🔔 New item found for '{keywords}': Found {len(items_ids_diff)} new items.")
                    last_items[encoded_arguments].extend(list(items_ids_diff))
                    last_items_updated = True
                    for item_id in items_ids_diff:
                        item = items_map[item_id]
                        item_title = item.get("title", "No title")
                        item_price = item.get("price", {"amount": "No", "currency": "price"})
                        item_price = f'{item_price.get("amount", "n/a")} {item_price.get("currency", "")}'.strip()
                        item_url = f'{URL_WALLAPOP_MAIN_ITEM}{urllib.parse.quote_plus(item.get("web_slug", ""))}'
                        notify_new_item(item_title, item_price, item_url)
                else:
                    log.debug(f"⏸ No new items for '{keywords}'.")
        # Removing unused queries
        for query in unused_queries:
            last_items_updated = True     
            del last_items[query]
            log.debug(f"Removed unused query: {query}")
    except requests.exceptions.RequestException as e:
        log.error(f"Request error: {e}")
    except Exception as e:
        log.error(f"Something went wrong: {e}")
        log.error(traceback.format_exc())
    if last_items_updated:
        save_last_items(last_items)
    return True

def init_logger():
    log.setLevel(logging.DEBUG)
    handler = logging.FileHandler(get_file_path(FILENAME_LOG), encoding='utf-8')
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    log.addHandler(console_handler)

def watcher(headers=None, fn_request_new_headers=None, clear_last_items=False):
    global last_items
    if not clear_last_items:
        last_items = load_last_items()
    else:
        last_items = {}
        save_last_items(last_items)
    log.debug("Starting watch...")

    if not headers:
        headers = load_headers_template()
    else:
        save_headers_template(headers)

    while True:
        if (not headers) or (not check_for_items(headers)) :
            headers = {}
            if fn_request_new_headers:
                headers = fn_request_new_headers()
            if not headers:
                show_message("Token missing", "No token entered. Closing app.")
                notify_error("No valid token. Wallapop watch stopped")
                return
            save_headers_template(headers)
        time.sleep(OPTION_TIMEOUT_BETWEEN_GROUP_REQUESTS)

def main():
    global STORAGE_PATH, OPTION_OPEN_BROWSER
    import argparse
    parser = argparse.ArgumentParser(description="Wallapop Monitor")
    parser.add_argument('--storage-path', type=str, default=STORAGE_PATH, help='Path to store configuration files')
    parser.add_argument('--request-file', type=str, default=None, help='Path to a file containing the fetch(...) request to extract headers and token')
    parser.add_argument('--windows-mode', action='store_true', help='Run in Windows mode (ask for new headers if needed)')
    parser.add_argument('--clear-cache', action='store_true', help='Clear saved last items cache')
    args = parser.parse_args()
    STORAGE_PATH = args.storage_path
    windows_mode = args.windows_mode and (platform.system() == "Windows")
    clear_cache = args.clear_cache
    OPTION_OPEN_BROWSER = windows_mode
                        
    init_logger()
    headers = None

    if args.request_file:
        if os.path.exists(args.request_file):
            with open(args.request_file, "rt", encoding="utf8") as file:
                fetch_request = file.read()
            try:
                headers, token = extract_headers_from_copied_fetch_request(fetch_request)
                if not headers:
                    log.error("No headers extracted from the provided file.")
                else:
                    log.debug(f"[DEBUG] Token from file: '{token}'")
            except Exception as e:
                log.error(f"Error extracting headers from file: {e}")
        else:
            log.error(f"Provided request file does not exist or is empty: {args.request_file}")

    watcher(headers=headers, fn_request_new_headers=ask_for_new_headers if windows_mode else None, clear_last_items=clear_cache)


if __name__ == "__main__":
    main()
