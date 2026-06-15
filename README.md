# SyncCollection (HTML-Only Version)

This is a simplified, standalone version of the SyncCollection tool. It focuses entirely on processing exported HTML files from LastSticker, removing the need for automated browsers or external scraping libraries.

## 🚀 Getting Started

### Prerequisites
Ensure you have Python installed, then install the required libraries:
```bash
pip install -r requirements.txt
```

### Running the App
```bash
streamlit run app.py
```

---

## 🛠 How to Export Data from LastSticker

Since this version does not fetch data automatically, you must manually provide the HTML content from LastSticker. Follow these steps to ensure the data is captured correctly:

### Step 1: Visit the Page
Choose the correct URL on [LastSticker.com](https://www.laststicker.com) based on what you want to sync:

*   **User Collections**: `https://www.laststicker.com/user/[YOUR_USERNAME]/collections`
*   **Specific Album (Standard)**: `https://www.laststicker.com/cards/[ALBUM_ID]`
*   **Specific Album (Extended)**: `https://www.laststicker.com/cards/[ALBUM_ID]/checklist`
*   **Category Checklist (List of Albums)**: `https://www.laststicker.com/cards/s/[CATEGORY_ID]`

### Step 2: Export the HTML
1.  **Right-click** anywhere on the page and select **Inspect** (or press `F12`).
2.  In the Elements tab, find the `<html>` or `<body>` tag.
3.  **Right-click** on the tag and select **Copy** -> **Copy outerHTML**.
4.  Open a text editor (like Notepad) and **Paste** the content.
5.  **Save the file** with a `.html` extension (e.g., `my_collection.html`).

> [!TIP]
> Alternatively, you can simply press `Ctrl + S` (Windows) or `Cmd + S` (Mac) to save the entire webpage as "Webpage, HTML Only".

### Step 3: Sync
1.  Open the SyncCollection app in your browser.
2.  Select the corresponding page from the sidebar (User Collections, Specific Album, etc.).
3.  **Drag and drop** your saved `.html` file into the upload area.
4.  The app will instantly parse the data and provide **JSON** and **CSV** download options.

---

## 📋 Available Features
*   **User Collections**: Extracts all "Needed" and "Offered" stickers across your entire profile.
*   **Specific Album**: Compares Standard and Extended checklists and generates individual CSVs.
*   **Category Checklist**: Generates a master list of all albums within a specific Category (e.g., FIFA World Cup).

## 🗂 File Structure
*   `app.py`: The core Streamlit application.
*   `requirements.txt`: Minimal dependencies (No Playwright/Cloudscraper needed).
