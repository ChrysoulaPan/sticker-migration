import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import json

st.set_page_config(page_title="SyncCollection", page_icon="📓", layout="wide")

page = st.sidebar.radio("Navigation", ["User Collections", "Specific Album"])

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_html(url):
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"ERROR: {e}"

def parse_stickers(text_block):
    """
    Parses a block of text containing stickers like "1, 2 (2), 5, 8 (3), 10" 
    Returns a dictionary of {sticker_number: count}
    """
    if not text_block:
        return {}
    
    stickers = {}
    # Split by comma
    parts = [p.strip() for p in text_block.split(',')]
    for p in parts:
        if not p:
            continue
        
        # Check for multiplicity in parentheses e.g., "123 (2)"
        match = re.search(r'^(.*?)\s*\((\d+)\)$', p)
        if match:
            sticker_id = match.group(1).strip()
            count = int(match.group(2))
        else:
            # Maybe just a number or name, e.g., "123"
            sticker_id = p.strip()
            count = 1
            
        if sticker_id:
            stickers[sticker_id] = count
            
    return stickers

def extract_all_collections(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    
    # User said: exchange lists are inside head_inner
    blocks = soup.find_all('div', class_='head_inner')
    for i, block in enumerate(blocks):
        # Finding the collection name
        name = ""
        album_item = block.find('div', class_='album_item')
        if album_item:
            h3 = album_item.find(['h3', 'h4', 'b'])
            if h3 and h3.text.strip():
                name = h3.text.strip()
            else:
                links = album_item.find_all('a', href=re.compile(r'^/cards/'))
                for l in links:
                    if l.text.strip():
                        name = l.text.strip()
                        break
        
        if not name or name == "Collections":
            continue

        # JS Mapping: some stickers are rendered via JS arrays
        js_data = {}
        scripts = block.find_all('script')
        # Also check siblings just in case script is outside head_inner but relates to it
        next_sib = block.find_next_sibling('script')
        if next_sib:
            scripts.append(next_sib)
            
        for script in scripts:
            script_text = script.get_text()
            if 'print_card_list' in script_text:
                try:
                    # IDs: cl[0] = ['id1','id2',...]
                    ids_match = re.search(r"cl\[0\]\s*=\s*\[(.*?)\];", script_text)
                    # Counts: cl[2] = [1,2,...]
                    counts_match = re.search(r"cl\[2\]\s*=\s*\[(.*?)\];", script_text)
                    # Div ID: print_card_list(cl, ..., 'div_id', ...)
                    div_id_match = re.search(r"print_card_list\s*\(\s*cl\s*,\s*.*?\s*,\s*'(.*?)'", script_text)
                    
                    if ids_match and counts_match and div_id_match:
                        div_id = div_id_match.group(1)
                        # Extract IDs by removing quotes and splitting
                        raw_ids = re.findall(r"['\"]([^'\"]+)['\"]", ids_match.group(1))
                        # Extract Counts by splitting commas
                        raw_counts = counts_match.group(1).split(',')
                        
                        ids = [x.strip() for x in raw_ids]
                        counts = []
                        for c in raw_counts:
                            try:
                                counts.append(int(c.strip()))
                            except:
                                counts.append(1)
                        
                        stickers = []
                        # Zip them up. Usually lengths match.
                        for id_val, count_val in zip(ids, counts):
                            for _ in range(max(1, count_val)):
                                stickers.append(id_val)
                        
                        js_data[div_id] = stickers
                except:
                    pass

        exchange_lists = block.find_all('div', class_=lambda c: c and 'exchange_list' in c and 'cards_tooltip' in c)
        
        needed_list = []
        offered_list = []
        
        for t in exchange_lists:
            t_id = t.get('id', '')
            is_need = 'c_to_' in t_id
            is_offer = 'c_from_' in t_id
            
            stickers_found = []
            
            # 1. Use JS data if available for this div
            if t_id in js_data:
                stickers_found = js_data[t_id]
            
            # 2. Fallback to HTML parsing if JS data is missing or empty
            if not stickers_found:
                links = t.find_all('a')
                for a in links:
                    sticker_id = a.get_text(strip=True)
                    if not sticker_id:
                        continue
                    
                    multiplier = 1
                    span = a.find_next_sibling('span')
                    if span and '(' in span.text and ')' in span.text:
                        try:
                            multiplier_text = re.search(r'\((\d+)\)', span.text)
                            if multiplier_text:
                                multiplier = int(multiplier_text.group(1))
                        except:
                            pass
                    
                    for _ in range(multiplier):
                        stickers_found.append(sticker_id)

            if is_need:
                needed_list.extend(stickers_found)
            elif is_offer:
                offered_list.extend(stickers_found)
                    
        if name or needed_list or offered_list:
            results.append({
                "Collection Name": name,
                "Stickers Needed": ", ".join(needed_list),
                "Stickers Offered": ", ".join(offered_list)
            })
            
    return results

if page == "User Collections":
    st.title("📓 SyncCollection")
    st.markdown("Scrape user collections for needed and offered stickers.")

    username = st.text_input("Username", placeholder="e.g. stickeristas123")
    sync_button = st.button("Sync Collection", type="primary")

    if sync_button and username:
        username = username.strip()
        with st.spinner(f"Fetching collections for user: {username}..."):
            # Branding removed from UI, but URL remains the same internal logic
            main_url = f"https://www.laststicker.com/user/{username}/collections"
            html = fetch_html(main_url)
            
            if html.startswith("ERROR:"):
                st.error(f"Failed to fetch data. Please check the username.")
            else:
                results = extract_all_collections(html)
                print(f"DEBUG: Extracted {len(results)} results")
                
                if not results:
                    st.warning(f"No active data found for user '{username}'.")
                else:
                    st.success(f"Found {len(results)} collections.")
                    
                    st.subheader("Results")
                    
                    # Show JSON
                    with st.expander("View JSON Output", expanded=True):
                        st.json(results)
                        
                    # Download CSV
                    if results:
                        df = pd.DataFrame(results)
                        csv = df.to_csv(index=False).encode('utf-8')
                        
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"{username}_collections.csv",
                            mime="text/csv",
                        )

elif page == "Specific Album":
    st.title("📓 Sync Specific Album")
    st.markdown("Scrape album checklist to get a list of all stickers.")

    album_id = st.text_input("Album ID", placeholder="e.g. topps_uefa_champions_league_2025-2026")
    sync_album_button = st.button("Sync Album", type="primary")

    if sync_album_button and album_id:
        album_id = album_id.strip()
        with st.spinner(f"Fetching checklist for album: {album_id}..."):
            url = f"https://www.laststicker.com/cards/{album_id}/checklist"
            html = fetch_html(url)
            
            if html.startswith("ERROR:"):
                st.error("Failed to fetch data. Please check the album ID.")
            else:
                soup = BeautifulSoup(html, 'html.parser')
                checklist_table = soup.find('table', id='checklist')
                
                # Requested debug logging to console
                if checklist_table:
                    print(f"--- DEBUG: Checklist HTML Start ---\n{checklist_table.prettify()[:1500]}\n--- DEBUG: Checklist HTML End ---")
                else:
                    print("--- DEBUG: No checklist table found ---")

                # Extract Album Info
                name = ""
                h1 = soup.find('h1')
                if h1:
                    name = h1.text.replace("Checklist", "").strip()
                
                year = ""
                total_stickers = ""
                big_text = soup.find('p', class_='big_text')
                if big_text:
                    spans = big_text.find_all('span')
                    for span in spans:
                        text = span.text.strip()
                        if "Year:" in text:
                            year = text.replace("Year:", "").strip()
                        elif "Total stickers:" in text:
                            total_stickers = text.replace("Total stickers:", "").strip()
                
                # Extract Stickers
                stickers = []
                if checklist_table:
                    tbody = checklist_table.find('tbody')
                    rows = tbody.find_all('tr') if tbody else checklist_table.find_all('tr')
                    for row in rows:
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 4:
                            no = cols[0].get_text(strip=True)
                            title = cols[1].get_text(strip=True)
                            section = cols[2].get_text(strip=True)
                            type_ = cols[3].get_text(strip=True)
                            
                            if no.lower() == "no." or title.lower() == "title":
                                continue
                            
                            stickers.append({
                                "No.": no,
                                "Title": title,
                                "Section": section,
                                "Type": type_,
                                "Category": "sticker"
                            })
                
                st.subheader("Album Information")
                col1, col2, col3 = st.columns(3)
                col1.metric("Album Name", name if name else "Unknown")
                col2.metric("Year", year if year else "Unknown")
                col3.metric("Total Stickers", total_stickers if total_stickers else "Unknown")
                
                if not stickers:
                    st.warning("No stickers found in the checklist.")
                else:
                    st.success(f"Extracted {len(stickers)} stickers.")
                    
                    st.subheader("Results")
                    with st.expander("View JSON Output", expanded=True):
                        st.json(stickers)
                        
                    df = pd.DataFrame(stickers)
                    csv = df.to_csv(index=False).encode('utf-8')
                    
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"{album_id}_checklist.csv",
                        mime="text/csv",
                    )
