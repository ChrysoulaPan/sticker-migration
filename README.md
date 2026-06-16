# SyncCollection

A hybrid sticker collection sync tool. Some pages use drag & drop HTML upload; album checklist pages use an automated browser popup.

## 🚀 Navigation

| Page | Method | URL to export/fetch from LastSticker |
|---|---|---|
| **User from file** | Drag & Drop | `laststicker.com/user/[USERNAME]/collections` |
| **Standard Album** | Automated Browser | `laststicker.com/cards/[ALBUM_ID]` |
| **Extended Album** | Automated Browser | `laststicker.com/cards/[ALBUM_ID]/checklist` |
| **Album from file** | Drag & Drop | `laststicker.com/cards/[ALBUM_ID]` or `/checklist` |
| **Album Checklist from file** | Drag & Drop | `laststicker.com/cards/s/[CATEGORY_ID]` |

---

## 🛠 How to Export HTML (for Drag & Drop pages)

1. Visit the corresponding LastSticker URL in your browser.
2. Right-click anywhere on the page → **Inspect** (or press `F12`).
3. In the **Elements** tab, find the `<html>` tag.
4. Right-click it → **Copy** → **Copy outerHTML**.
5. Paste into a text editor (e.g. Notepad) and save as a `.html` file.
6. Drag and drop the saved file into the app's upload area.

> [!TIP]
> Alternatively, press `Ctrl + S` in your browser and save as **"Webpage, HTML Only"** for a quick export.

---

## 🤖 Automated Browser Pages (Standard & Extended Album)

The **Standard Album** and **Extended Album** pages open a visible browser popup to fetch data automatically.

1. Enter the Album ID (e.g. `panini_world_cup_2026`) — or paste the full LastSticker URL.
2. Click **Verify to Sync**.
3. A Chromium browser window will open and navigate to the album page.
4. If a **Cloudflare challenge** appears, solve it manually in the popup.
5. Once the checklist table is visible, the app detects it automatically and captures the data.

> [!IMPORTANT]
> The browser window **must remain visible** so you can interact with Cloudflare challenges.

---

## ⚙️ Prerequisites

```bash
pip install -r requirements.txt
py -m playwright install chromium
```

## ▶️ Running the App

```bash
streamlit run app.py
```
