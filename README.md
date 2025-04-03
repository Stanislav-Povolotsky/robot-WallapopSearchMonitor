# 🧭 Wallapop Search Monitor

This is a Python script that monitors your **saved searches** on [Wallapop](https://www.wallapop.com) and notifies you when new items appear — opening the result in your default browser.

Made to run on Windows and designed for easy `.exe` packaging — no terminal or Python needed for the end user.

---

## 🚀 Features

- ✅ Uses your personal **Wallapop token**
- ✅ Monitors your **saved alerts** (`/searchalerts/savedsearch`)
- ✅ Automatically opens your default browser when new items are posted
- ✅ Runs in the background every 10 seconds
- ✅ Works with `.exe` generated via PyInstaller

---

## 🛠 Requirements

- Python 3.10+ (for development and `.exe` generation)
- Windows (uses Notepad to input token)
- `pyinstaller` (`pip install pyinstaller`)

> ✅ Final `.exe` runs on any Windows without needing Python installed

---

## 🔐 How to Get Your Wallapop Token

1. Log into [https://www.wallapop.com](https://www.wallapop.com)
2. Open your browser dev tools (usually F12)
3. Go to the **Network** tab
4. Refresh the page
5. Look for a request to `/me`
6. Open the request headers and find this line:

