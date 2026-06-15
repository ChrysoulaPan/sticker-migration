import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="SyncCollection (HTML Only)", page_icon="📓", layout="wide")

# Navigation logic
page_options = ["User Collections", "Specific Album", "Generate Album Checklist"]
page = st.sidebar.radio("Navigation", page_options)

def parse_stickers(text_block):
    if not text_block:
        return {}
    stickers = {}
    parts = [p.strip() for p in text_block.split(',')]
    for p in parts:
        if not p: continue
        match = re.search(r'^(.*?)\s*\((\d+)\)$', p)
        if match:
            sticker_id = match.group(1).strip()
            count = int(match.group(2))
        else:
            sticker_id = p.strip()
            count = 1
        if sticker_id:
            stickers[sticker_id] = count
    return stickers

def extract_all_collections(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    blocks = soup.find_all('div', class_='head_inner')
    for i, block in enumerate(blocks):
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
        if not name or name == "Collections": continue

        js_data = {}
        scripts = block.find_all('script')
        next_sib = block.find_next_sibling('script')
        if next_sib: scripts.append(next_sib)
            
        for script in scripts:
            script_text = script.get_text()
            if 'print_card_list' in script_text:
                try:
                    ids_match = re.search(r"cl\[0\]\s*=\s*\[(.*?)\]", script_text)
                    counts_match = re.search(r"cl\[2\]\s*=\s*\[(.*?)\]", script_text)
                    div_id_match = re.search(r"print_card_list\s*\(\s*cl\s*,\s*[^,]*\s*,\s*['\"]([^'\"]+)['\"]", script_text)
                    if ids_match and counts_match and div_id_match:
                        div_id = div_id_match.group(1)
                        raw_ids = re.findall(r"['\"]([^'\"]*)['\"]", ids_match.group(1))
                        raw_counts = counts_match.group(1).split(',')
                        ids = [x.strip() for x in raw_ids if x.strip()]
                        counts = []
                        for c in raw_counts:
                            try: counts.append(int(c.strip()))
                            except: counts.append(1)
                        stickers = []
                        for id_val, count_val in zip(ids, counts):
                            for _ in range(max(1, count_val)): stickers.append(id_val)
                        if stickers: js_data[div_id] = stickers
                except: pass

        exchange_lists = block.find_all('div', class_=lambda c: c and 'exchange_list' in c and 'cards_tooltip' in c)
        needed_list = []
        offered_list = []
        for t in exchange_lists:
            t_id = t.get('id', '')
            is_need = 'c_to_' in t_id
            is_offer = 'c_from_' in t_id
            stickers_found = []
            if t_id in js_data: stickers_found = js_data[t_id]
            if not stickers_found:
                links = t.find_all('a')
                for a in links:
                    sticker_id = a.get_text(strip=True)
                    if not sticker_id: continue
                    multiplier = 1
                    span = a.find_next_sibling('span')
                    if span and '(' in span.text and ')' in span.text:
                        try:
                            multiplier_text = re.search(r'\((\d+)\)', span.text)
                            if multiplier_text: multiplier = int(multiplier_text.group(1))
                        except: pass
                    for _ in range(multiplier): stickers_found.append(sticker_id)
            if is_need: needed_list.extend(stickers_found)
            elif is_offer: offered_list.extend(stickers_found)
        if name or needed_list or offered_list:
            results.append({
                "Collection Name": name,
                "Stickers Needed": ", ".join(needed_list),
                "Stickers Offered": ", ".join(offered_list)
            })
    return results

def extract_stickers_from_html(html, category_option):
    soup = BeautifulSoup(html, 'html.parser')
    checklist_table = soup.find('table', id='checklist')
    name = ""
    h1 = soup.find('h1')
    if h1: name = h1.text.replace("Checklist", "").strip()
    year = ""; total_stickers_text = ""; total_type = ""
    big_text = soup.find('p', class_='big_text')
    if big_text:
        spans = big_text.find_all('span')
        for span in spans:
            text = span.text.strip()
            if "Year:" in text: year = text.replace("Year:", "").strip()
            elif "Total stickers:" in text:
                total_stickers_text = text.replace("Total stickers:", "").strip()
                total_type = "stickers"
            elif "Total cards:" in text:
                total_stickers_text = text.replace("Total cards:", "").strip()
                total_type = "cards"
    total_count = 0
    if total_stickers_text:
        try: total_count = int("".join([c for c in total_stickers_text if c.isdigit()]))
        except: pass
    stickers = []
    if checklist_table:
        tbody = checklist_table.find('tbody')
        rows = tbody.find_all('tr') if tbody else checklist_table.find_all('tr')
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 4:
                no = cols[0].get_text(strip=True); title = cols[1].get_text(strip=True)
                section = cols[2].get_text(strip=True); type_ = cols[3].get_text(strip=True)
                if no.lower() == "no." or title.lower() == "title": continue
                if category_option == "Cards" or (category_option == "Mixed" and "Card" in type_): category = "card"
                else: category = "sticker"
                stickers.append({"No.": no, "Title": title, "Section": section, "Type": type_, "Category": category})
    return name, year, total_stickers_text, total_type, total_count, stickers

def process_results(results, source_name):
    if not results:
        st.warning("No data found.")
    else:
        st.success(f"Found {len(results)} collections.")
        st.subheader("Results")
        with st.expander("View JSON Output", expanded=True): st.json(results)
        df = pd.DataFrame(results)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download CSV", data=csv, file_name=f"{source_name}_collections.csv", mime="text/csv")

def process_album_data(html_standard, html_extended, album_id, category_option):
    name, year, total_text, total_type, total_count, standard_stickers = extract_stickers_from_html(html_standard, category_option)
    name_ext, year_ext, total_text_ext, total_type_ext, total_count_ext, extended_stickers = extract_stickers_from_html(html_extended, category_option)
    final_name = name if name else name_ext
    final_year = year if year else year_ext
    total_display = total_text if total_text else total_text_ext
    has_diff = False; base_stickers = []; full_stickers = []
    if len(standard_stickers) > 0 and len(extended_stickers) > 0:
        if len(standard_stickers) != len(extended_stickers):
            has_diff = True; base_stickers = standard_stickers; full_stickers = extended_stickers
        else: full_stickers = standard_stickers
    elif len(standard_stickers) > 0:
        full_stickers = standard_stickers
        if total_count > 0 and len(full_stickers) > total_count:
            has_diff = True; base_stickers = full_stickers[:total_count]
    elif len(extended_stickers) > 0:
        full_stickers = extended_stickers
        eff_total = total_count_ext if total_count_ext > 0 else total_count
        if eff_total > 0 and len(full_stickers) > eff_total:
            has_diff = True; base_stickers = full_stickers[:eff_total]
    
    st.subheader("Album Information")
    st.metric("Album Name", final_name if final_name else "Unknown")
    st.metric("Year", final_year if final_year else "Unknown")
    st.metric("Total Count", total_display if total_display else "Unknown")
    
    if not full_stickers:
        st.warning("No stickers found.")
    else:
        if has_diff:
            st.success(f"Extracted standard ({len(base_stickers)}) and extended ({len(full_stickers)}) versions.")
            tab1, tab2 = st.tabs(["Standard", "Extended"])
            with tab1:
                st.write(f"Standard Version ({len(base_stickers)})")
                st.json(base_stickers)
                st.download_button("Download Standard CSV", pd.DataFrame(base_stickers).to_csv(index=False).encode('utf-8'), f"{album_id}_standard.csv", "text/csv")
            with tab2:
                st.write(f"Extended Version ({len(full_stickers)})")
                st.json(full_stickers)
                st.download_button("Download Extended CSV", pd.DataFrame(full_stickers).to_csv(index=False).encode('utf-8'), f"{album_id}_extended.csv", "text/csv")
        else:
            st.success(f"Extracted {len(full_stickers)} stickers.")
            st.json(full_stickers)
            st.download_button("Download CSV", pd.DataFrame(full_stickers).to_csv(index=False).encode('utf-8'), f"{album_id}_checklist.csv", "text/csv")

def process_category_html(html, category_id, item_type_option):
    soup = BeautifulSoup(html, 'html.parser')
    album_items = soup.find_all('div', class_='album_item')
    albums = []
    for item in album_items:
        a_tag = item.find('a', href=True)
        album_link_id = ""
        if a_tag:
            href = a_tag['href']
            parts = [p for p in href.split('/') if p]
            if len(parts) >= 2 and parts[0] == "cards": album_link_id = parts[1].replace("-checklist", "").strip()
        h3 = item.find('h3')
        if h3:
            full_text = h3.text.strip(); desc = full_text; publisher = ""
            b_tag = h3.find('b')
            if b_tag: desc = b_tag.text.strip()
            match = re.search(r'\(([^)]+)\)$', full_text)
            if match:
                publisher = match.group(1).strip()
                if not b_tag: desc = full_text[:match.start()].strip()
            year = ""; total_items = ""; category = ""
            spans = item.find_all('span')
            for span in spans:
                span_text = span.text.strip()
                if "Year:" in span_text: year = span_text.replace("Year:", "").strip()
                elif "Total stickers:" in span_text: total_items = span_text.replace("Total stickers:", "").strip(); category = "Stickers"
                elif "Total cards:" in span_text: total_items = span_text.replace("Total cards:", "").strip(); category = "Cards"
            albums.append({"Album": desc, "Publisher": publisher, "Year": year, "Total": total_items, "Category": category})
    if albums:
        st.success(f"Found {len(albums)} albums.")
        st.dataframe(pd.DataFrame(albums))
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: pd.DataFrame(albums).to_excel(writer, index=False)
        st.download_button("Download Excel", output.getvalue(), f"{category_id}_albums.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if page == "User Collections":
    st.title("📓 User Collections (Drag & Drop)")
    uploaded_file = st.file_uploader("Drop User Collections HTML", type=["html"])
    if uploaded_file:
        html = uploaded_file.read().decode("utf-8", errors="ignore")
        results = extract_all_collections(html)
        process_results(results, "collections")
elif page == "Specific Album":
    st.title("📓 Specific Album (Drag & Drop)")
    uploaded_file = st.file_uploader("Drop Album Checklist HTML", type=["html"])
    cat = st.radio("Category", ["Stickers", "Cards", "Mixed"], index=2)
    if uploaded_file:
        html = uploaded_file.read().decode("utf-8", errors="ignore")
        process_album_data(html, "", "album", cat)
elif page == "Generate Album Checklist":
    st.title("📓 Generate Category Checklist (Drag & Drop)")
    uploaded_file = st.file_uploader("Drop Category Page HTML", type=["html"])
    if uploaded_file:
        html = uploaded_file.read().decode("utf-8", errors="ignore")
        process_category_html(html, "category", "Both")
