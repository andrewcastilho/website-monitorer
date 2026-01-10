from playwright.sync_api import sync_playwright
import json
import os
import requests

URL = "https://sitedetailsreport.sfwmd.gov/#/sites/S44"
STATE_FILE = "last_value.json"

def get_gate_value():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)

        # Wait for the table value to load
        page.wait_for_timeout(8000)

        text = page.content()
        browser.close()

    # Look for gate opening value in page text
    import re
    match = re.search(r"Gate Opening.*?([0-9]+\.[0-9]+)", text, re.S)
    if not match:
        raise Exception("Gate Opening value not found")

    return float(match.group(1))

def load_last():
    if not os.path.exists(STATE_FILE):
        return 0.0
    return json.load(open(STATE_FILE))["value"]

def save_last(value):
    json.dump({"value": value}, open(STATE_FILE, "w"))

def notify(value):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.environ["PUSHOVER_TOKEN"],
            "user": os.environ["PUSHOVER_USER"],
            "message": f"S44 Gate OPENING ALERT 🚨\nGate Opening: {value} ft"
        }
    )

current = get_gate_value()
last = load_last()

if current > 0.0 and last == 0.0:
    notify(current)

save_last(current)
