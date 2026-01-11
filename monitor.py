#!/usr/bin/env python3
"""
Spillway Gate Monitor - Using correct SFWMD API endpoints
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

# Base URL from your findings
BASE_URL = "https://sitedetailsreport.sfwmd.gov"

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

def get_flow_from_realtime(structure):
    """
    Get flow data from realtime endpoint
    URL: https://sitedetailsreport.sfwmd.gov/realtime?format=json&sites=S40&status=A
    """
    try:
        url = f"{BASE_URL}/realtime"
        params = {
            "format": "json",
            "sites": structure,
            "status": "A"
        }
        
        logger.debug(f"Fetching realtime data for {structure}")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Save raw response for debugging
        with open(f"realtime_{structure}.json", "w") as f:
            json.dump(data, f, indent=2)
        
        # Parse the response based on actual structure
        # The API returns an array of objects
        if isinstance(data, list) and len(data) > 0:
            for item in data:
                # Look for discharge/flow data
                # Common field names based on typical hydrology APIs
                if "discharge" in item:
                    flow_value = item["discharge"]
                elif "flow" in item:
                    flow_value = item["flow"]
                elif "value" in item:
                    flow_value = item["value"]
                else:
                    # Try to find any numeric value that could be flow
                    for key, value in item.items():
                        if isinstance(value, (int, float)) and key.lower() not in ["id", "timestamp", "date"]:
                            flow_value = value
                            break
                    else:
                        continue
                
                try:
                    flow_float = float(flow_value)
                    logger.info(f"Found flow for {structure}: {flow_float} cfs")
                    return flow_float
                except (ValueError, TypeError):
                    continue
        
        logger.warning(f"No flow data found in realtime response for {structure}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting realtime data for {structure}: {e}")
        return None

def get_flow_from_mdm(structure):
    """
    Get flow data from mdm endpoint (backup)
    URL: https://sitedetailsreport.sfwmd.gov/mdm?site=S40
    """
    try:
        url = f"{BASE_URL}/mdm"
        params = {"site": structure}
        
        logger.debug(f"Fetching mdm data for {structure}")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Save raw response for debugging
        with open(f"mdm_{structure}.json", "w") as f:
            json.dump(data, f, indent=2)
        
        # MDM endpoint might have different structure
        # Look for flow/discharge data
        if isinstance(data, dict):
            # Check common field names
            for field in ["discharge", "flow", "discharge_cfs", "flow_cfs", "value"]:
                if field in data:
                    try:
                        flow_value = float(data[field])
                        logger.info(f"Found flow in mdm for {structure}: {flow_value} cfs")
                        return flow_value
                    except (ValueError, TypeError):
                        continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting mdm data for {structure}: {e}")
        return None

def get_flow(structure):
    """
    Main function to get flow - tries realtime first, then mdm
    """
    # Try realtime endpoint first
    flow = get_flow_from_realtime(structure)
    
    # If realtime fails, try mdm endpoint
    if flow is None:
        logger.info(f"Realtime failed for {structure}, trying mdm endpoint...")
        flow = get_flow_from_mdm(structure)
    
    return flow

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
    """Main monitoring function"""
    logger.info("Starting spillway monitor with correct API endpoints...")
    
    # Check if Pushover credentials are set
    if not os.environ.get("PUSHOVER_TOKEN") or not os.environ.get("PUSHOVER_USER"):
        logger.warning("Pushover credentials not found in environment")
        logger.warning("Notifications will not be sent")
    
    check_structures()
    logger.info("Check completed")

if __name__ == "__main__":
    main()
