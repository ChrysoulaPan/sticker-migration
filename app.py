import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import json
from io import BytesIO

st.set_page_config(page_title="SyncCollection", page_icon="📓", layout="wide")

query_params = st.query_params
initial_page = "User Collections"
initial_album_id = ""

if "page" in query_params:
    page_q = query_params["page"]
    if page_q in ["User Collections", "Specific Album", "Generate Album Checklist"]:
        initial_page = page_q

if "album_id" in query_params:
    initial_album_id = query_params["album_id"]

page_options = ["User Collections", "Specific Album", "Generate Album Checklist"]
page = st.sidebar.radio("Navigation", page_options, index=page_options.index(initial_page))

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

def extract_stickers_from_html(html, category_option):
    if html.startswith("ERROR:"):
        return "", "", "", "", 0, []
        
    soup = BeautifulSoup(html, 'html.parser')
    checklist_table = soup.find('table', id='checklist')
    
    # Extract Album Info
    name = ""
    h1 = soup.find('h1')
    if h1:
        name = h1.text.replace("Checklist", "").strip()
    
    year = ""
    total_stickers_text = ""
    total_type = ""
    big_text = soup.find('p', class_='big_text')
    if big_text:
        spans = big_text.find_all('span')
        for span in spans:
            text = span.text.strip()
            if "Year:" in text:
                year = text.replace("Year:", "").strip()
            elif "Total stickers:" in text:
                total_stickers_text = text.replace("Total stickers:", "").strip()
                total_type = "stickers"
            elif "Total cards:" in text:
                total_stickers_text = text.replace("Total cards:", "").strip()
                total_type = "cards"
    total_count = 0
    if total_stickers_text:
        try:
            total_count = int("".join([c for c in total_stickers_text if c.isdigit()]))
        except:
            pass
            
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
                
                if category_option == "Cards" or (category_option == "Mixed" and "Card" in type_):
                    category = "card"
                else:
                    category = "sticker"
                        
                stickers.append({
                    "No.": no,
                    "Title": title,
                    "Section": section,
                    "Type": type_,
                    "Category": category
                })
                
    return name, year, total_stickers_text, total_type, total_count, stickers

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

    album_id = st.text_input("Album ID", value=initial_album_id, placeholder="e.g. topps_uefa_champions_league_2025-2026")
    category_option = st.radio("Select category",["Stickers","Cards","Mixed"], index=2)   
    sync_album_button = st.button("Sync Album", type="primary")

    auto_run = False
    if initial_album_id and getattr(st.session_state, 'last_auto_album', None) != initial_album_id:
        st.session_state.last_auto_album = initial_album_id
        auto_run = True

    if (sync_album_button or auto_run) and album_id and category_option:
        album_id = album_id.strip()
        if album_id.endswith("/checklist"):
            album_id = album_id[:-10]
            
        with st.spinner(f"Fetching checklist details for album: {album_id}..."):
            url_standard = f"https://www.laststicker.com/cards/{album_id}"
            url_extended = f"https://www.laststicker.com/cards/{album_id}/checklist"
            
            html_standard = fetch_html(url_standard)
            html_extended = fetch_html(url_extended)
            
            if html_standard.startswith("ERROR:") and html_extended.startswith("ERROR:"):
                st.error("Failed to fetch data. Please check the album ID.")
            else:
                name, year, total_text, total_type, total_count, standard_stickers = extract_stickers_from_html(html_standard, category_option)
                name_ext, year_ext, total_text_ext, total_type_ext, total_count_ext, extended_stickers = extract_stickers_from_html(html_extended, category_option)
                
                # Consolidate metadata
                final_name = name if name else name_ext
                final_year = year if year else year_ext
                
                total_display = "Unknown"
                if total_text and total_text_ext and total_text != total_text_ext:
                    total_display = f"{total_text} (Std) / {total_text_ext} (Ext)"
                elif total_text:
                    total_display = total_text
                elif total_text_ext:
                    total_display = total_text_ext
                
                # Determine standard and extended lists
                has_diff = False
                base_stickers = []
                full_stickers = []
                
                if len(standard_stickers) != len(extended_stickers) and len(standard_stickers) > 0 and len(extended_stickers) > 0:
                    has_diff = True
                    base_stickers = standard_stickers
                    full_stickers = extended_stickers
                elif len(standard_stickers) > 0:
                    full_stickers = standard_stickers
                    if total_count > 0 and len(full_stickers) > total_count:
                        has_diff = True
                        base_stickers = full_stickers[:total_count]
                elif len(extended_stickers) > 0:
                    full_stickers = extended_stickers
                    if total_count_ext > 0 and len(full_stickers) > total_count_ext:
                        has_diff = True
                        base_stickers = full_stickers[:total_count_ext]
                        
                final_total_type = total_type if total_text else total_type_ext
                metric_title = "Stated total cards" if final_total_type == "cards" else "Stated total stickers"
                
                st.subheader("Album Information")
                col1, col2, col3 = st.columns(3)
                col1.metric("Album Name", final_name if final_name else "Unknown")
                col2.metric("Year", final_year if final_year else "Unknown")
                col3.metric(metric_title, total_display)
                
                if not full_stickers:
                    st.warning("No stickers found in the checklist.")
                else:
                    if has_diff:
                        st.success(f"Extracted standard version ({len(base_stickers)} items) and extended version ({len(full_stickers)} items).")
                        st.subheader("Results")
                        
                        tab1, tab2 = st.tabs(["Standard Checklist", "Extended Checklist"])
                        
                        with tab1:
                            st.write(f"**Standard Version ({len(base_stickers)} items)**")
                            with st.expander("View JSON Output", expanded=True):
                                st.json(base_stickers)
                                
                            df_base = pd.DataFrame(base_stickers)
                            csv_base = df_base.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="Download Standard CSV",
                                data=csv_base,
                                file_name=f"{album_id}_standard.csv",
                                mime="text/csv",
                                key="download_standard"
                            )
                            
                        with tab2:
                            st.write(f"**Extended Version ({len(full_stickers)} items)**")
                            with st.expander("View JSON Output", expanded=True):
                                st.json(full_stickers)
                                
                            df_full = pd.DataFrame(full_stickers)
                            csv_full = df_full.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="Download Extended CSV",
                                data=csv_full,
                                file_name=f"{album_id}_extended.csv",
                                mime="text/csv",
                                key="download_extended"
                            )
                    else:
                        st.success(f"Extracted {len(full_stickers)} stickers.")
                        st.subheader("Results")
                        with st.expander("View JSON Output", expanded=True):
                            st.json(full_stickers)
                            
                        df = pd.DataFrame(full_stickers)
                        csv = df.to_csv(index=False).encode('utf-8')
                        
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"{album_id}_checklist.csv",
                            mime="text/csv",
                        )

elif page == "Generate Album Checklist":
    st.title("📓 Generate Album Checklist")
    st.markdown("Generate an Excel checklist of all albums under a specific category.")

    if 'checklist_category_id' not in st.session_state:
        st.session_state['checklist_category_id'] = ""
    if 'checklist_item_type' not in st.session_state:
        st.session_state['checklist_item_type'] = "Both"
    if 'albums_data' not in st.session_state:
        st.session_state['albums_data'] = None

    category_id = st.text_input("Category ID", placeholder="e.g. uefa_european_championship")
    item_type_option = st.radio("Item Type", ["Both", "Stickers", "Cards"], index=0)
    generate_button = st.button("Generate Checklist", type="primary")

    if generate_button and category_id:
        category_id = category_id.strip()
        st.session_state['checklist_category_id'] = category_id
        st.session_state['checklist_item_type'] = item_type_option
        with st.spinner(f"Fetching {item_type_option.lower()} albums for category: {category_id}..."):
            if item_type_option == "Both":
                url = f"https://www.laststicker.com/cards/s/{category_id}"
            elif item_type_option == "Stickers":
                url = f"https://www.laststicker.com/cards/s1/{category_id}"
            elif item_type_option == "Cards":
                url = f"https://www.laststicker.com/cards/s2/{category_id}"
                
            html = fetch_html(url)
            
            if html.startswith("ERROR:"):
                st.error("Failed to fetch data. Please check the category ID.")
                st.session_state['albums_data'] = None
            else:
                soup = BeautifulSoup(html, 'html.parser')
                album_items = soup.find_all('div', class_='album_item')
                
                albums = []
                for item in album_items:
                    a_tag = item.find('a', href=True)
                    album_link_id = ""
                    if a_tag:
                        href = a_tag['href']
                        parts = [p for p in href.split('/') if p]
                        if len(parts) >= 2 and parts[0] == "cards":
                            album_link_id = parts[1].replace("-checklist", "").strip()
                            if album_link_id.endswith("- checklist"):
                                album_link_id = album_link_id[:-11].strip()

                    h3 = item.find('h3')
                    if h3:
                        full_text = h3.text.strip()
                        desc = full_text
                        publisher = ""
                        
                        b_tag = h3.find('b')
                        if b_tag:
                            desc = b_tag.text.strip()
                            
                        # Parse out Publisher in parenthesis at the end of the full h3 text
                        match = re.search(r'\(([^)]+)\)$', full_text)
                        if match:
                            publisher = match.group(1).strip()
                            if not b_tag:
                                desc = full_text[:match.start()].strip()
                                
                        year = ""
                        total_items = ""
                        category = ""
                        
                        spans = item.find_all('span')
                        for span in spans:
                            span_text = span.text.strip()
                            if "Year:" in span_text:
                                year = span_text.replace("Year:", "").strip()
                            elif "Total stickers:" in span_text:
                                total_items = span_text.replace("Total stickers:", "").strip()
                                category = "Stickers"
                            elif "Total cards:" in span_text:
                                total_items = span_text.replace("Total cards:", "").strip()
                                category = "Cards"
                                
                        albums.append({
                            "Link": f"/?page=Specific+Album&album_id={album_link_id}" if album_link_id else "",
                            "Album Description": desc,
                            "Publisher": publisher,
                            "Year": year,
                            "Total Count": total_items,
                            "Category": category,
                            "Stickeristas": False
                        })
                st.session_state['albums_data'] = albums
                            
    if st.session_state.get('albums_data') is not None and \
       st.session_state.get('checklist_category_id') == category_id.strip() and \
       st.session_state.get('checklist_item_type') == item_type_option:
        albums = st.session_state['albums_data']
        if not albums:
            st.warning("No albums found for this category.")
        else:
            st.success(f"Found {len(albums)} albums.")
            
            df = pd.DataFrame(albums)
            
            st.subheader("Results")
            edited_df = st.data_editor(
                df,
                column_config={
                    "Link": st.column_config.LinkColumn(
                        "🔗 Sync",
                        display_text="Open ↗"
                    ),
                    "Stickeristas": st.column_config.CheckboxColumn(
                        "Stickeristas",
                        help="Check if you have this album",
                        default=False,
                    )
                },
                disabled=["Link", "Album Description", "Publisher", "Year", "Total Count", "Category"],
                hide_index=True,
                use_container_width=True
            )
            
            df_export = edited_df.copy()
            if "Link" in df_export:
                df_export = df_export.drop("Link", axis=1)
            df_export["Stickeristas"] = df_export["Stickeristas"].apply(lambda x: True if x else "")
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Checklist')
            
            st.download_button(
                label="Download Excel",
                data=output.getvalue(),
                file_name=f"{category_id}_albums_{item_type_option.lower()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

