# SyncCollection

SyncCollection is a web application that extracts sticker collections and specific album checklists from LastSticker. This helps collectors keep track of their progress offline or manage their lists in custom databases. The application is built using Python, Streamlit, and BeautifulSoup for HTML parsing.

## Features
- **User Collections**: Sync an entire user profile to extract detailed lists of all needed and offered stickers across their active collections.
- **Specific Album Checklist**: Sync a specific album to download its full checklist as a CSV, complete with `No.`, `Title`, `Section`, `Type`, and a default `Category`.

## Prerequisites
To run this application locally, you will need Python 3 installed. Python 3.8 or later is recommended.
The application depends on the following third-party libraries:
- `streamlit`
- `pandas`
- `beautifulsoup4`
- `cloudscraper`

## Setup & Execution

### Windows
1. Double-click the provided `run.bat` file in the project folder.
2. The batch script will automatically install any missing dependencies and then start the Streamlit application.
3. A local server will start, and the UI will automatically open in your default web browser at `http://localhost:8501`.

### macOS / Linux / Manual Execution
1. Open your terminal or command prompt.
2. Navigate to the project directory.
3. Install the required dependencies using pip:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

## Navigating the Application

The application has a dynamic sidebar that provides two main pages to choose from:

1. **User Collections**
   - **Enter a Username** (e.g., your username or any public profile).
   - **Click "Sync Collection"**.
   - The app will securely connect, fetch the list of active collections, and securely extract checklists of needed and offered stickers.
   - You can review the output in the JSON expander and click **Download CSV** to save the result.

2. **Specific Album**
   - **Enter an Album ID** (e.g., `topps_uefa_champions_league_2025-2026`). You can find this ID in the album's direct URL.
   - **Click "Sync Album"**.
   - The app scrapes the full checklist, providing a complete breakdown. It displays basic metrics about the album like Name, Year, and the Total amount of Stickers.
   - You can also view the raw JSON data inside the expander and hit **Download CSV** for the complete tabular checklist.
