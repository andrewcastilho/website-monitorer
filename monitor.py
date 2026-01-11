#!/usr/bin/env python3
"""
Spillway Gate Monitor - Using WORKING SFWMD API endpoint
"""

import requests
import json
import os
import logging
from datetime import datetime
from pathlib import Path

# Configuration
STRUCTURES = ["S44", "S41", "S155", "S40"]
STATE_FILE = Path("data/last_values.json")
LOG_FILE = Path("logs/monitor.log")

SURGE_THRESHOLD = 500  # cfs jump that counts as a surge

# WORKING API endpoint from your original cURL command
API_URL = "https://my.sfwmd.gov/dbhydroplsql/web_io.report_process"

# Headers from your WORKING cURL command
HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'origin': 'https://sitedetailsreport.sfwmd.gov',
    'priority': 'u=1, i',
    'referer': 'https://sitedetailsreport.sfwmd.gov/',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
}

# Setup logging
def setup_logging():
    """Configure logging"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def load_state():
    """Load last known flow values"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading state: {e}")
        return {}

def save_state(state):
    """Save current flow values"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state: {e}")

def notify(structure, flow, delta=None):
    """Send Pushover notification"""
    try:
        token = os.environ.get("PUSHOVER_TOKEN")
        user = os.environ.get("PUSHOVER_USER")
        
        if not token or not user:
            logger.error("Pushover credentials not set")
            return False
        
        msg = f"🚨 {structure} FLOW ALERT\nFlow: {flow} cfs"
        if delta:
            msg += f"\nSurge: +{delta} cfs"
        msg += f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": token,
                "user": user,
                "message": msg,
                "title": "Spillway Alert",
                "priority": 1
            },
            timeout=30
        )
        response.raise_for_status()
        logger.info(f"Notification sent for {structure}")
        return True
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False

def get_flow(structure):
    """
    Get flow data from the WORKING DBHYDRO API endpoint
    Returns: flow value in cfs or None if error
    """
    try:
        # EXACT form data from your working cURL command
        form_data = {
            "v_target_flag": "public",
            "v_report_type": "format6",
            "v_site_list": structure,
            "v_datatype_list": "flow",  # Changed from "gate" to get flow
            "v_begin_date": datetime.now().strftime("%Y-%m-%d"),
            "v_end_date": datetime.now().strftime("%Y-%m-%d"),
            "v_show_raw": "Y",
            "v_show_summary": "N",
            "v_show_approved": "Y",
            "v_show_provisional": "Y"
        }
        
        logger.debug(f"Fetching flow for {structure} from WORKING API")
        
        # IMPORTANT: Use verify=False to bypass SSL certificate error
        response = requests.post(
            API_URL,
            data=form_data,
            headers=HEADERS,
            timeout=30,
            verify=False  # ← THIS IS KEY for SSL bypass
        )
        
        # Debug logging
        logger.debug(f"Status: {response.status_code}")
        logger.debug(f"URL: {response.url}")
        
        if response.status_code != 200:
            logger.error(f"API returned status {response.status_code} for {structure}")
            logger.error(f"Response: {response.text[:200]}")
            return None
        
        # Parse the JSON response
        try:
            data = response.json()
            logger.debug(f"Successfully parsed JSON for {structure}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for {structure}: {e}")
            logger.error(f"Response content type: {response.headers.get('content-type')}")
            logger.error(f"Response first 500 chars: {response.text[:500]}")
            return None
        
        # Navigate the JSON structure - EXACTLY as in your JSON file
        if "timeSeriesResponse" in data and "timeSeries" in data["timeSeriesResponse"]:
            time_series_list = data["timeSeriesResponse"]["timeSeries"]
            
            logger.debug(f"Found {len(time_series_list)} time series for {structure}")
            
            # Look for FLOW parameter (checking multiple possibilities)
            for time_series in time_series_list:
                param = time_series.get("parameter", {})
                param_name = param.get("parameterName", "")
                unit_code = param.get("unit", {}).get("unitCode", "")
                
                # Check for flow data (cfs)
                if param_name == "FLOW" and unit_code == "cfs":
                    if "values" in time_series and len(time_series["values"]) > 0:
                        latest_value = time_series["values"][0]
                        if "value" in latest_value:
                            flow_value = latest_value["value"]
                            timestamp = latest_value.get("dateTime", "No timestamp")
                            logger.info(f"Got flow for {structure}: {flow_value} cfs at {timestamp}")
                            return float(flow_value)
                
                # Also check for gate openings if flow not found
                elif param_name == "GATE OPENING":
                    if "values" in time_series and len(time_series["values"]) > 0:
                        latest_value = time_series["values"][0]
                        if "value" in latest_value:
                            gate_value = latest_value["value"]
                            logger.debug(f"Gate opening for {structure}: {gate_value} ft")
        
        logger.warning(f"No flow data found in response for {structure}")
        # Log the available parameters for debugging
        for i, ts in enumerate(time_series_list):
            param = ts.get("parameter", {})
            logger.debug(f"Series {i}: {param.get('parameterName')} ({param.get('unit', {}).get('unitCode')})")
        
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error fetching data for {structure}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching flow for {structure}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def check_structures():
    """Check all structures for flow changes"""
    state = load_state()
    changes_detected = False
    
    for structure in STRUCTURES:
        try:
            logger.info(f"Checking {structure}...")
            
            current = get_flow(structure)
            
            if current is None:
                logger.warning(f"Could not retrieve flow for {structure}")
                continue
                
            last = state.get(structure)
            
            if last is None:  # First reading
                logger.info(f"{structure}: {current} cfs (first reading)")
                
                # OPTIONAL: Alert if gate is already open on first check
                if current > 0:
                    logger.info(f"Gate already open on first check: {structure}")
                    # Uncomment the line below to get alert for already open gates
                    # notify(structure, current, None)
            
            else:  # Subsequent readings
                logger.info(f"{structure}: {current} cfs (last: {last} cfs, delta: {current - last:.1f} cfs)")
                
                # Gate opens (transition from 0 to >0)
                if current > 0 and last == 0:
                    logger.info(f"Gate opening detected for {structure}")
                    notify(structure, current)
                    changes_detected = True
                
                # Surge detection
                elif current - last >= SURGE_THRESHOLD:
                    delta = current - last
                    logger.info(f"Surge detected for {structure}: +{delta} cfs")
                    notify(structure, current, delta)
                    changes_detected = True
            
            state[structure] = current
            
        except Exception as e:
            logger.error(f"Error checking {structure}: {e}")
    
    if changes_detected:
        save_state(state)
    else:
        # Still save state even if no changes, to track values
        save_state(state)
    
    return changes_detected

def main():
    """Main monitoring function"""
    logger.info("Starting spillway monitor with WORKING API...")
    
    # Check if Pushover credentials are set
    if not os.environ.get("PUSHOVER_TOKEN") or not os.environ.get("PUSHOVER_USER"):
        logger.warning("Pushover credentials not found in environment")
        logger.warning("Notifications will not be sent")
    
    check_structures()
    logger.info("Check completed")

if __name__ == "__main__":
    main()
