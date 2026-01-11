#!/usr/bin/env python3
"""
Spillway Gate Monitor
Monitors SFWMD DBHYDRO flow data and sends notifications when spillway gates open.
"""

import requests
import json
import os
import logging
from datetime import datetime
import time
from pathlib import Path

# Configuration
STRUCTURES = ["S44", "S41", "S155", "S40"]
STATE_FILE = Path("data/last_values.json")
LOG_FILE = Path("logs/monitor.log")
CONFIG_FILE = Path("config/config.json")

SURGE_THRESHOLD = 500  # cfs jump that counts as a surge

# API Configuration
DBHYDRO_URL = "https://www.sfwmd.gov/dbhydroplsql/web_io.report_process"
PARAMS = {
    "v_target": "stage_flow",
    "v_run_mode": "onLine",
    "v_js_flag": "Y",
    "v_report_type": "format",
    "v_period": "uspec",
    "v_date_type": "date"
}

# Setup logging
def setup_logging():
    """Configure logging to both file and console"""
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
    """Load last known flow values from state file"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading state: {e}")
        return {}

def save_state(state):
    """Save current flow values to state file"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state: {e}")

def notify(structure, flow, delta=None):
    """
    Send notification via Pushover
    Returns: True if successful, False otherwise
    """
    try:
        token = os.environ.get("PUSHOVER_TOKEN")
        user = os.environ.get("PUSHOVER_USER")
        
        if not token or not user:
            logger.error("Pushover credentials not set in environment variables")
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
                "priority": 1,
                "timestamp": int(time.time())
            },
            timeout=30
        )
        response.raise_for_status()
        logger.info(f"Notification sent for {structure}")
        return True
    except Exception as e:
        logger.error(f"Error sending notification for {structure}: {e}")
        return False

def get_flow(structure):
    """
    Fetch flow data for a specific structure from DBHYDRO
    Returns: flow value in cfs or None if error
    """
    try:
        params = PARAMS.copy()
        params.update({
            "v_station": structure,
            "v_dbkey": get_dbkey(structure),
            "v_start_date": datetime.now().strftime("%m/%d/%Y"),
            "v_end_date": datetime.now().strftime("%m/%d/%Y"),
            "v_format": "json"
        })
        
        logger.debug(f"Fetching data for {structure} with params: {params}")
        
        response = requests.get(DBHYDRO_URL, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # The API returns data in different format, need to parse accordingly
        if isinstance(data, list) and len(data) > 0:
            # Extract flow value from the response
            # Adjust this parsing based on actual API response structure
            for item in data:
                if "data_value" in item:
                    try:
                        flow_value = float(item["data_value"])
                        return flow_value
                    except (ValueError, TypeError):
                        continue
        
        logger.warning(f"No valid flow data found for {structure}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error fetching data for {structure}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for {structure}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching flow for {structure}: {e}")
        return None

def get_dbkey(structure):
    """
    Map structure IDs to DBKEY values used by DBHYDRO API
    You may need to adjust these based on actual DBHYDRO database keys
    """
    dbkey_map = {
        "S44": "FLA02379",  # Example, need actual DBKEY values
        "S41": "FLA02376",  # Example, need actual DBKEY values
        "S155": "FLA02370", # Example, need actual DBKEY values
        "S40": "FLA02373"   # Example, need actual DBKEY values
    }
    return dbkey_map.get(structure, structure)

def check_structures():
    """Check all configured structures for flow changes"""
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
            
            if last is not None:
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
            
            else:
                logger.info(f"{structure}: {current} cfs (first reading)")
            
            state[structure] = current
            
        except Exception as e:
            logger.error(f"Error checking {structure}: {e}")
    
    if changes_detected:
        save_state(state)
    
    return changes_detected

def main():
    """Main monitoring loop"""
    logger.info("Starting spillway monitor...")
    
    # Load configuration if exists
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            # Update structures from config if present
            if "structures" in config:
                global STRUCTURES
                STRUCTURES = config["structures"]
                logger.info(f"Loaded {len(STRUCTURES)} structures from config")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    # Check environment variables
    if not os.environ.get("PUSHOVER_TOKEN") or not os.environ.get("PUSHOVER_USER"):
        logger.warning("Pushover credentials not found in environment variables")
        logger.warning("Set PUSHOVER_TOKEN and PUSHOVER_USER environment variables")
    
    # Run single check
    check_structures()
    logger.info("Check completed")

if __name__ == "__main__":
    main()
