# 🧭 Wallapop Search Monitor

This is a Python script that monitors your **saved searches** on [Wallapop](https://www.wallapop.com) and notifies you when new items appear — opening the result in your default browser.

Made to run on Windows and designed for easy `.exe` packaging — no terminal or Python needed for the end user.

---

## 🚀 Features

- ✅ Uses your personal **Wallapop token**
- ✅ Monitors your **saved alerts** (`/searchalerts/savedsearch`)
- ✅ Automatically opens your default browser when new items are posted
- ✅ Runs in the background every 10 seconds
- ✅ No console or terminal needed
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
2. Open your browser dev tools (usually Ctrl + Shift + I )
3. Go to the **Network** tab
4. Refresh the page
5. Look for a request to `/me`
6. Open the request headers and find this line:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOi...
```

7. Copy only the token (everything **after** `Bearer `)

---

## ▶️ How to Use

1. Run the script:

```bash
python wallapop_monitor.py
```

2. A Notepad window will open asking you to paste your Wallapop token
3. Replace the sample line with your token, press `Ctrl+S` to save, and close Notepad
4. The script starts running and checks for updates every 10 seconds

---

## 📦 Build the .EXE

To create a Windows `.exe` that runs without a console:

```bash
pyinstaller --onefile wallapop_monitor.py
```

Output will be in the `dist/` folder:
```
dist\wallapop_monitor.exe
```

---

## 🗂 Where is the token saved?

Your token is saved to:

```
%APPDATA%\wallapop_python_token.txt
```

You can delete that file to be prompted again.

---
---

## 👤 Author

Made with ❤️ by **Telmo Ferreira**  
Feel free to fork, open issues, or contribute.

---

## 📄 License

MIT License — use it freely, just don't resell it.
