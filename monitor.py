import requests
import json
import os

STRUCTURES = ["S44", "S41", "S155", "S40"]
STATE_FILE = "last_values.json"

DBHYDRO_URL = "https://api.dbhydro.sfwmd.gov/v1/data"

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def notify(structure, flow):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.environ["PUSHOVER_TOKEN"],
            "user": os.environ["PUSHOVER_USER"],
            "message": f"🚨 {structure} FLOW DETECTED\nFlow: {flow} cfs"
        }
    )

def get_flow_value(structure):
    params = {
        "site_id": structure,
        "parameter": "DISCHARGE",
        "format": "json",
        "limit": 1,
        "order": "desc"
    }

    r = requests.get(DBHYDRO_URL, params=params, timeout=30)
    r.raise_for_status()

    data = r.json()

    if not data or "value" not in data[0]:
        raise Exception("No flow data returned")

    return float(data[0]["value"])

def main():
    state = load_state()

    for structure in STRUCTURES:
        try:
            current = get_flow_value(structure)
            last = state.get(structure, 0.0)

            print(f"{structure}: {current} cfs (last: {last})")

            # Notify on 0 → >0 transition
            if current > 0 and last == 0:
                notify(structure, current)

            state[structure] = current

        except Exception as e:
            print(f"Error checking {structure}: {e}")

    save_state(state)

if __name__ == "__main__":
    main()
