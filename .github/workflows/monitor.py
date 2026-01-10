import requests
import json
import os

URL = "https://sitedetailsreport.sfwmd.gov/#/sites/S44"  # ← CHANGE THIS
STATE_FILE = "last_value.json"

def get_value():
    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    return r.text[:200]  # temporary: detects ANY change

def load_last():
    if not os.path.exists(STATE_FILE):
        return None
    return json.load(open(STATE_FILE))["value"]

def save_last(value):
    json.dump({"value": value}, open(STATE_FILE, "w"))

def notify(value):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.environ["PUSHOVER_TOKEN"],
            "user": os.environ["PUSHOVER_USER"],
            "message": "Website changed!"
        }
    )

current = get_value()
last = load_last()

if current != last:
    notify(current)
    save_last(current)
