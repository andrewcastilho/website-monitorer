from playwright.sync_api import sync_playwright
import json
import os
import requests
import re

# 🔧 STRUCTURES TO MONITOR
STRUCTURES = {
    "S44": "https://sitedetailsreport.sfwmd.gov/#/sites/S44",
    "S41": "https://sitedetailsreport.sfwmd.gov/#/sites/S41",
    "S155": "https://sitedetailsreport.sfwmd.gov/#/sites/S155",
    "S40": "https://sitedetailsreport.sfwmd.gov/#/sites/S40",
}

STATE_FILE = "last_values.json"
SIGNIFICANT_CHANGE_CFS = 500  # notify if flow increases by this much

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    return json.load(open(STATE_FILE))

def save_state(state):
    json.dump(state, open(STATE_FILE, "w"))

def notify(structure, value, change=None):
    message = f"🚨 {structure} FLOW ALERT\nFlow: {value} cfs"
    if change:
        message += f" (+{change} cfs)"
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.environ["PUSHOVER_TOKEN"],
            "user": os.environ["PUSHOVER_USER"],
            "message": message
        }
    )

def get_flow_value(page, url):
    page.goto(url, timeout=60000)
    page.wait_for_timeout(8000)  # wait for dynamic content

    text = page.content()

    # Extract flow in cfs
    match = re.search(r"Flow.*?([0-9,]+\.[0-9]+)\s*cfs", text, re.S)
    if not match:
        raise Exception("Flow value not found")

    return float(match.group(1).replace(",", ""))

def main():
    state = load_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for structure, url in STRUCTURES.items():
            try:
                current = get_flow_value(page, url)
                last = state.get(structure, 0.0)

                print(f"{structure}: {current} cfs (last: {last})")

                # Notify when flow goes from 0 → >0
                if current > 0.0 and last == 0.0:
                    notify(structure, current)

                # Notify on significant increase
                elif current - last >= SIGNIFICANT_CHANGE_CFS:
                    notify(structure, current, change=current - last)

                state[structure] = current

            except Exception as e:
                print(f"Error checking {structure}: {e}")

        browser.close()

    save_state(state)

if __name__ == "__main__":
    main()
