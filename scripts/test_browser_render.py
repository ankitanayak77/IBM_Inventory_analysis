import os
import subprocess
import tempfile
import sys

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:5000"

PAGES = [
    "/dashboard",
    "/products",
    "/inventory",
    "/sales",
    "/restock",
    "/analytics",
    "/recommendations",
    "/reports",
    "/products/1",
    "/sales/829262"
]

def test_page(page):
    url = BASE_URL + page
    out_dir = os.environ.get("TEMP", tempfile.gettempdir())
    safe_name = page.replace("/", "_").strip("_") or "dashboard"
    screenshot_file = os.path.join(out_dir, f"shot_{safe_name}.png")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={temp_dir}",
            f"--screenshot={screenshot_file}",
            "--window-size=1280,2200",
            url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        shot_exists = os.path.exists(screenshot_file)
        size = os.path.getsize(screenshot_file) if shot_exists else 0
        
        # Also run dump-dom
        cmd_dom = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            f"--user-data-dir={temp_dir}",
            "--dump-dom",
            url
        ]
        res_dom = subprocess.run(cmd_dom, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        dom_len = len(res_dom.stdout) if res_dom.stdout else 0
        
        print(f"PAGE: {page:<20} | Screenshot: {shot_exists} ({size} bytes) | DOM length: {dom_len} | RetCode: {res.returncode}")
        if res.stderr:
            lines = [l.strip() for l in res.stderr.splitlines() if l.strip()]
            if lines:
                print("   stderr:", lines[:2])

if __name__ == "__main__":
    for p in PAGES:
        test_page(p)
