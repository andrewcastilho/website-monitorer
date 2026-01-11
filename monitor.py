import requests
import json
import os

STRUCTURES = ["S44", "S41", "S155", "S40"]
STATE_FILE = "last_values.json"

SURGE_THRESHOLD = 500  # cfs jump that counts as a surge

DBHYDRO_URL = "https://www.sfwmd.gov/dbhydroplsql/web_io.report_process"

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def notify(structure, flow, delta=None):
    msg = f"🚨 {structure} FLOW ALERT\nFlow: {flow} cfs"
    if delta:
        msg += f"\nSurge: +{delta} cfs"

    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.environ["PUSHOVER_TOKEN"],
            "user": os.environ["PUSHOVER_USER"],
            "message": msg
        }
    )

def get_flow(structure):
    params = {
        "v_report_type": "station_data",
        "v_station": structure,
        "v_param": "FLOW",
        "v_num_records": 1,
        "v_format": "json"
    }

    r = requests.get(DBHYDRO_URL, params=params, timeout=30)
    r.raise_for_status()

    data = r.json()

    if "data" not in data or not data["data"]:
        raise Exception("No flow data returned")

    return float(data["data"][0]["value"])

def main():
    state = load_state()

    for structure in STRUCTURES:
        try:
            current = get_flow(structure)
            last = state.get(structure, 0.0)

            print(f"{structure}: {current} cfs (last: {last})")

            # Gate opens
            if current > 0 and last == 0:
                notify(structure, current)

            # Surge detection
            elif current - last >= SURGE_THRESHOLD:
                notify(structure, current, current - last)

            state[structure] = current

        except Exception as e:
            print(f"Error checking {structure}: {e}")

    save_state(state)

if __name__ == "__main__":
    main()

