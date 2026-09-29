import os
import subprocess
import tempfile
import sys
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:5000"
ARTIFACTS_DIR = Path(os.environ.get("TEMP", tempfile.gettempdir())) / "inventory_auth_screenshots"

PAGES = [
    ("/login", "shot_auth_login.png", ["Sign In", "Password", "Keep me signed in"]),
    ("/signup", "shot_auth_signup.png", ["Create Your Account", "Full Name", "Password Strength"]),
    ("/dashboard", "shot_auth_unauth_redirect.png", ["Sign In"]),  # Unauth redirect to login
]

def run_headless_tests():
    print("=" * 65)
    print("STARTING HEADLESS CHROME BROWSER AUTH UI VALIDATION")
    print("=" * 65)

    if not os.path.exists(CHROME_PATH):
        print(f"Chrome not found at {CHROME_PATH}")
        sys.exit(1)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    for route, shot_name, expected_strings in PAGES:
        url = BASE_URL + route
        shot_path = ARTIFACTS_DIR / shot_name

        with tempfile.TemporaryDirectory() as temp_dir:
            cmd = [
                CHROME_PATH,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={temp_dir}",
                f"--screenshot={str(shot_path)}",
                "--window-size=1280,1000",
                "--dump-dom",
                url
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
            dom = res.stdout or ""
            shot_exists = shot_path.exists()
            shot_size = shot_path.stat().st_size if shot_exists else 0

            # Verify DOM content
            missing = [s for s in expected_strings if s not in dom]
            if missing:
                print(f"FAIL {route}: Missing expected text in DOM: {missing}")
                sys.exit(1)

            print(f"PASS {route:<15} | Screenshot: {shot_exists} ({shot_size:,} bytes) | DOM: {len(dom):,} bytes | RetCode: {res.returncode}")

    print("=" * 65)
    print("ALL HEADLESS CHROME BROWSER AUTH PAGES RENDERED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    run_headless_tests()
