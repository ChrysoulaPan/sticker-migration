import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
from io import BytesIO

# Try to import playwright for Standard/Extended pages
try:
    from scraper_utils import fetch_with_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

st.set_page_config(page_title="SyncCollection", page_icon="📓", layout="wide")

use_interactive = True
use_headful = True

# Navigation
page_options = ["User from file", "Standard Album", "Extended Album", "Album from file", "Album Checklist from file"]
page = st.sidebar.radio("Navigation", page_options)

# Parsing Utilities
def extract_all_collections(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    blocks = soup.find_all('div', class_='head_inner')
    for block in blocks:
        name = ""
        album_item = block.find('div', class_='album_item')
        if album_item:
            h3 = album_item.find(['h3', 'h4', 'b'])
            name = h3.text.strip() if h3 else ""
            if not name:
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
                        counts = [int(c.strip()) if c.strip().isdigit() else 1 for c in raw_counts]
                        stickers = []
                        for id_val, count_val in zip(ids, counts):
                            for _ in range(max(1, count_val)): stickers.append(id_val)
                        if stickers: js_data[div_id] = stickers
                except: pass
        exchange_lists = block.find_all('div', class_=lambda c: c and 'exchange_list' in c and 'cards_tooltip' in c)
        needed, offered = [], []
        for t in exchange_lists:
            t_id = t.get('id', '')
            stickers = js_data[t_id] if t_id in js_data else []
            if not stickers:
                for a in t.find_all('a'):
                    sid = a.get_text(strip=True)
                    if not sid: continue
                    m = 1
                    s = a.find_next_sibling('span')
                    if s and '(' in s.text:
                        mt = re.search(r'\((\d+)\)', s.text)
                        if mt: m = int(mt.group(1))
                    for _ in range(m): stickers.append(sid)
            if 'c_to_' in t_id: needed.extend(stickers)
            elif 'c_from_' in t_id: offered.extend(stickers)
        if name or needed or offered:
            results.append({"Collection Name": name, "Stickers Needed": ", ".join(needed), "Stickers Offered": ", ".join(offered)})
    return results

def extract_stickers_from_html(html, category_option):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='checklist')
    name = soup.find('h1').text.replace("Checklist", "").strip() if soup.find('h1') else ""
    year, total_text, t_type, t_count = "", "", "", 0
    bt = soup.find('p', class_='big_text')
    if bt:
        for span in bt.find_all('span'):
            txt = span.text.strip()
            if "Year:" in txt: year = txt.replace("Year:", "").strip()
            elif "Total stickers:" in txt: total_text = txt.replace("Total stickers:", "").strip(); t_type = "stickers"
            elif "Total cards:" in txt: total_text = txt.replace("Total cards:", "").strip(); t_type = "cards"
    if total_text:
        try: t_count = int("".join([c for c in total_text if c.isdigit()]))
        except: pass
    stickers = []
    if table:
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 4:
                no, title, sec, typ = [c.get_text(strip=True) for c in cols[:4]]
                if no.lower() == "no." or title.lower() == "title": continue
                cat = "card" if (category_option == "Cards" or (category_option == "Mixed" and "Card" in typ)) else "sticker"
                stickers.append({"No.": no, "Title": title, "Section": sec, "Type": typ, "Category": cat})
    return name, year, total_text, t_type, t_count, stickers

def process_album_data(html_std, html_ext, aid, cat):
    n, y, t, tt, tc, s_std = extract_stickers_from_html(html_std, cat) if html_std else ("", "", "", "", 0, [])
    ne, ye, te, tte, tce, s_ext = extract_stickers_from_html(html_ext, cat) if html_ext else ("", "", "", "", 0, [])
    fn = n if n else ne; fy = y if y else ye; ft = t if t else te
    st.subheader("Album Information")
    st.metric("Album", fn); st.metric("Year", fy); st.metric("Total", ft)
    full = s_std if s_std else s_ext
    if not full: st.warning("No data found.")
    else:
        st.success(f"Found {len(full)} stickers.")
        st.json(full)
        st.download_button("Download CSV", pd.DataFrame(full).to_csv(index=False).encode('utf-8'), f"{aid}.csv", "text/csv")

def process_category_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all('div', class_='album_item')
    albums = []
    for item in items:
        a = item.find('a', href=True)
        aid = a['href'].split('/')[-2].replace("-checklist", "").strip() if a else ""
        h3 = item.find('h3')
        if h3:
            ft = h3.text.strip(); d = ft; p = ""
            b = h3.find('b')
            if b: d = b.text.strip()
            m = re.search(r'\(([^)]+)\)$', ft)
            if m:
                p = m.group(1).strip()
                if not b: d = ft[:m.start()].strip()
            yr, tot, cat = "", "", ""
            for span in item.find_all('span'):
                tx = span.text.strip()
                if "Year:" in tx: yr = tx.replace("Year:", "").strip()
                elif "Total stickers:" in tx: tot = tx.replace("Total stickers:", "").strip(); cat = "Stickers"
                elif "Total cards:" in tx: tot = tx.replace("Total cards:", "").strip(); cat = "Cards"
            albums.append({"Album Description": d, "Publisher": p, "Year": yr, "Total Count": tot, "Category": cat, "Stickeristas": False})
    return albums

# Render Pages
if page == "User from file":
    st.title("📓 User from file")
    up = st.file_uploader("Upload Collections HTML", type=["html"])
    if up:
        res = extract_all_collections(up.read().decode("utf-8", errors="ignore"))
        st.success(f"Found {len(res)} collections.")
        st.json(res)
        st.download_button("Download CSV", pd.DataFrame(res).to_csv(index=False).encode('utf-8'), "collections.csv", "text/csv")

elif page == "Standard Album":
    st.title("📓 Standard Album (Automated Browser)")
    aid = st.text_input("Album ID", placeholder="e.g. panini_podosfairo_1979-1980")
    cat = st.radio("Category", ["Stickers", "Cards", "Mixed"], index=2)
    if st.button("Verify to Sync") and aid:
        with st.spinner("Fetching..."):
            html = fetch_with_playwright(f"https://www.laststicker.com/cards/{aid}", None, None, headless=not use_headful, interactive=use_interactive, target_selector="table#checklist")
            process_album_data(html, "", aid, cat)

elif page == "Extended Album":
    st.title("📓 Extended Album (Automated Browser)")
    aid = st.text_input("Album ID", placeholder="e.g. panini_podosfairo_1979-1980")
    cat = st.radio("Category", ["Stickers", "Cards", "Mixed"], index=2)
    if st.button("Verify to Sync") and aid:
        with st.spinner("Fetching..."):
            html = fetch_with_playwright(f"https://www.laststicker.com/cards/{aid}/checklist", None, None, headless=not use_headful, interactive=use_interactive, target_selector="table#checklist")
            process_album_data("", html, aid, cat)

elif page == "Album from file":
    st.title("📓 Album from file")
    up = st.file_uploader("Upload Album HTML", type=["html"])
    cat = st.radio("Category", ["Stickers", "Cards", "Mixed"], index=2, key="spec_cat")
    if up:
        process_album_data(up.read().decode("utf-8", errors="ignore"), "", "uploaded", cat)

elif page == "Album Checklist from file":
    st.title("📓 Album Checklist from file")
    up = st.file_uploader("Upload Category Page HTML", type=["html"])
    if up:
        albums = process_category_html(up.read().decode("utf-8", errors="ignore"))
        if albums:
            st.success(f"Found {len(albums)} albums.")
            df = pd.DataFrame(albums)
            edited_df = st.data_editor(df, column_config={"Stickeristas": st.column_config.CheckboxColumn("Stickeristas", default=False)}, disabled=["Album Description", "Publisher", "Year", "Total Count", "Category"], hide_index=True, use_container_width=True)
            df_exp = edited_df.copy()
            df_exp["Stickeristas"] = df_exp["Stickeristas"].apply(lambda x: "Yes" if x else "")
            out = BytesIO()
            with pd.ExcelWriter(out, engine='openpyxl') as wr: df_exp.to_excel(wr, index=False)
            st.download_button("Download Excel", out.getvalue(), "albums.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
