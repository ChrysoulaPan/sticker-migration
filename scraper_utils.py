import os
import time
import threading
import asyncio
from playwright.sync_api import sync_playwright

# Temporarily disabled stealth to prevent 'module not callable' errors
# from playwright_stealth import stealth 

def fetch_with_playwright(url, username=None, password=None, headless=True, interactive=False, target_selector=None):
    """
    Experimental Playwright fetcher.
    Runs in a separate thread to avoid asyncio conflicts with Streamlit.
    """
    res = {"html": None, "error": None}

    def _playwright_task():
        try:
            # Fix for Windows: NotImplementedError with subprocesses
            if os.name == 'nt':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # Convert single url to list for uniform handling
                target_urls = [url] if isinstance(url, str) else url
                collected_html = []

                # Handle login once if automated
                if not interactive and username and password:
                    page.goto("https://www.laststicker.com/login")
                    time.sleep(1)
                    if page.locator('input[name="login"]').count() > 0:
                        page.fill('input[name="login"]', username)
                        page.fill('input[name="password"]', password)
                        page.click('button[type="submit"]')
                        page.wait_for_load_state("networkidle")
                
                for t_url in target_urls:
                    print(f"DEBUG: Navigating to {t_url}")
                    page.goto(t_url)
                    
                    if interactive:
                        print(f"DEBUG: [INTERACTIVE] Page opened. Waiting for user to reach target content on: {t_url}")
                        start_time = time.time()
                        last_status_time = 0
                        last_navigation_time = time.time()
                        navigation_retries = 0
                        max_navigation_retries = 3
                        
                        while time.time() - start_time < 300: 
                            try:
                                content = page.content()
                                current_url = page.url
                                
                                # NEW: Detect Human Verification (Cloudflare etc.)
                                is_verifying = "verify you are human" in content.lower() or "cloudflare" in content.lower() or "turnstile" in content.lower()
                                
                                # Use target selector if provided as CSS selector or substring
                                is_ready = False
                                if target_selector:
                                    if target_selector.startswith(".") or target_selector.startswith("#") or "table" in target_selector:
                                        is_ready = page.locator(target_selector).count() > 0
                                    else:
                                        is_ready = target_selector.lower() in content.lower()
                                else:
                                    # Fallback markers
                                    has_checklist = page.locator("table#checklist").count() > 0 or "print_card_list" in content
                                    has_exchange = "exchange_list" in content
                                    has_album = "album_item" in content
                                    has_collections_header = "head_inner" in content or "ico_coll_big" in content
                                    is_ready = has_checklist or has_exchange or has_album or has_collections_header
                                
                                # Determine page type for status message
                                page_type = "Checklist/Album"
                                if "/user/" in current_url and "/collections" in current_url:
                                    page_type = "User Collections"
                                elif "/cards/" in current_url:
                                    page_type = "Album Checklist"

                                # Periodic status update to terminal
                                if time.time() - last_status_time > 5:
                                    if is_verifying:
                                        print(f"DEBUG: [INTERACTIVE] ATTENTION: Cloudflare/Verification detected on {current_url}. Please solve it in the popup.")
                                    else:
                                        status_info = []
                                        if target_selector:
                                            status_info.append(f"Searching for '{target_selector}'")
                                        else:
                                            if has_checklist: status_info.append("Checklist Detected")
                                            if has_exchange: status_info.append("Exchange Lists Detected")
                                            if has_album or has_collections_header: status_info.append("Collections/Albums Detected")
                                        
                                        found_str = ", ".join(status_info) if status_info else "Waiting for content..."
                                        print(f"DEBUG: [INTERACTIVE] Page Type: {page_type} | URL: {current_url}")
                                        print(f"DEBUG: [INTERACTIVE] Status: {found_str}")
                                    last_status_time = time.time()

                                if is_ready:
                                    print(f"DEBUG: [INTERACTIVE] SUCCESS! Target content detected on {page_type} page.")
                                    print("DEBUG: [INTERACTIVE] Sleeping 3 seconds to ensure final rendering...")
                                    time.sleep(3)
                                    break
                                
                                # REDIRECT CHECK: If we are on a different URL than target, it might be a redundant redirect
                                if current_url.strip("/") != t_url.strip("/") and not is_verifying:
                                    # If we already have this URL in our collection, we might be able to skip
                                    # but let's just nudge back first
                                    pass

                                # AUTO-RENAVIGATE if we are stuck on the home page or login page
                                base_url = current_url.split("?")[0].rstrip("/")
                                is_on_home = base_url in ["https://www.laststicker.com", "http://www.laststicker.com", "https://laststicker.com", "http://laststicker.com"]
                                is_on_login = "/login" in current_url
                                
                                # Check if we need to login (common cause of redirects to home)
                                needs_login = ("log in" in content.lower() or "sing in" in content.lower()) and "/user/" in t_url
                                
                                # ONLY nudge if NOT currently verifying and enough time has passed
                                if (is_on_home or is_on_login) and (not is_verifying) and time.time() - last_navigation_time > 25:
                                    if navigation_retries < 2: # Keep it minimal
                                        reason = "Home Page Redirect" if is_on_home else "Login Page Redirect"
                                        if needs_login:
                                            print(f"DEBUG: [INTERACTIVE] NOTICE: Login required for this profile. Nudging to: {t_url}")
                                        else:
                                            print(f"DEBUG: [INTERACTIVE] Redirect detected. Nudging back to: {t_url}")
                                        
                                        page.goto(t_url)
                                        last_navigation_time = time.time()
                                        navigation_retries += 1
                                    else:
                                        # Stop nudging and just wait for user
                                        if time.time() - last_status_time > 60:
                                            print(f"DEBUG: [INTERACTIVE] NOTICE: Please manually navigate to {t_url} in the browser window.")
                                            last_status_time = time.time()

                            except Exception as e:
                                pass
                            time.sleep(1)
                    else:
                        print(f"DEBUG: [AUTOMATED] Waiting for page load on {t_url}...")
                        time.sleep(5)
                    
                    # Final capture with retry
                    for _ in range(3):
                        try:
                            # Verify page is not a 'Just a moment' Cloudflare page before final save
                            current_content = page.content()
                            if "verify you are human" in current_content.lower() and interactive:
                                print(f"DEBUG: [WARNING] Capturing a verification page for {t_url}. Results may be incomplete.")
                            collected_html.append(current_content)
                            break
                        except Exception:
                            time.sleep(1)
                
                res["html"] = collected_html if not isinstance(url, str) else collected_html[0]
                browser.close()
        except Exception as e:
            res["error"] = f"Browser Error: {str(e)}"

    # Launch in thread
    thread = threading.Thread(target=_playwright_task)
    thread.daemon = True # Ensure it doesn't hang the app
    thread.start()
    thread.join(timeout=310) # Slightly more than the loop timeout

    if res["error"]:
        return f"ERROR: Playwright failed: {res['error']}"
    if not res["html"]:
        return "ERROR: No content fetched. Did you close the browser window too early?"
    return res["html"]

if __name__ == "__main__":
    # Test block
    test_url = "https://www.laststicker.com/cards/panini_podosfairo_1979-1980"
    print("Testing Playwright fetch (headless=True)...")
    res = fetch_with_playwright(test_url, headless=True)
    if res.startswith("ERROR"):
        print(res)
    else:
        print(f"Success! Content length: {len(res)}")
