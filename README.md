# SyncCollection

SyncCollection is a web application that extracts sticker collections and specific album checklists from LastSticker. This helps collectors keep track of their progress offline or manage their lists in custom databases. The application is built using Python, Streamlit, and BeautifulSoup for HTML parsing.

## Features
- **User Collections**: Sync an entire user profile to extract detailed lists of all needed and offered stickers across their active collections.
- **Specific Album Checklist**: Sync a specific album to download its full checklist as a CSV, complete with `No.`, `Title`, `Section`, `Type`, and a default `Category`.
- **Generate Album Checklist**: Scrape an entire category (e.g. `uefa_european_championship`) to generate a master checklist of all released albums, exported as an interactive Excel file.

## Prerequisites
To run this application locally, you will need Python 3 installed. Python 3.8 or later is recommended.
The application depends on the following third-party libraries:
- `streamlit`
- `pandas`
- `beautifulsoup4`
- `cloudscraper`
- `openpyxl`

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

The application has a dynamic sidebar that provides three main pages to choose from:

1. **User Collections**
   - **Enter a Username** (e.g., your username or any public profile).
   - **Click "Sync Collection"**.
   - The app will securely connect, fetch the list of active collections, and securely extract checklists of needed and offered stickers.
   - You can review the output in the JSON expander and click **Download CSV** to save the result.

2. **Specific Album**
   - **Enter an Album ID** (e.g., `topps_uefa_champions_league_2025-2026`). You can find this ID in the album's direct URL. Alternatively, you can deep-link into this page from the Generate Album Checklist table.
   - **Select a category**: Choose whether you only want the row marked as `Stickers`, `Cards`, or `Mixed`. The app will assign the correct `Category` column property based on this toggle.
   - **Click "Sync Album"** (this happens automatically if navigating via deep-links).
   - The app scrapes the checklist, automatically checking both the standard album URL and the extended `/checklist` URL. It displays basic metrics about the album like Name, Year, and dynamically labels the stated total count as `Stated total stickers` or `Stated total cards`.
   - **Standard vs Extended**: If the standard and extended versions differ, or the stated total stickers is smaller than the full list, the app will separate them into tabs. You can view JSON data or download CSV files for either the **Standard Version** or **Extended Version**.

3. **Generate Album Checklist**
   - **Enter a Category ID** (e.g., `uefa_european_championship`). You can find this ID in a category's LastSticker URL.
   - **Select Item Type**: Choose to fetch "Both", "Stickers", or "Cards" via the radio button.
   - **Click "Generate Checklist"**.
   - The app scrapes all sub-albums within that specific category, extracting their Descriptions, Publishers, release Years, Total Count, and default Categories (Cards vs Stickers).
   - It will display an interactive table where you can track ownership via the `Stickeristas` checkboxes. The table intelligently preserves these selections as you browse around.
   - Click the **Open ↗** link in the `🔗 Sync` column to deep-link directly to that specific album's checklist in a new tab.
   - Click **Download Excel** to save the `.xlsx` file. Checked rows export as `TRUE`, and the filename dynamically specifies what was fetched (e.g. `category_albums_stickers.xlsx`).
