#!/usr/bin/env python3
"""
Spillway Gate Monitor - Using correct SFWMD API with proper headers
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

# API endpoint
API_URL = "https://sitedetailsreport.sfwmd.gov/realtime"

# Browser-like headers to get JSON instead of HTML
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
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
    Get flow data from the API with proper headers
    Returns: flow value in cfs or None if error
    """
    try:
        params = {
            "format": "json",
            "sites": structure,
            "status": "A"
        }
        
        logger.debug(f"Fetching data for {structure}")
        
        # Try with session first
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Make initial request to get cookies if needed
        session.get("https://sitedetailsreport.sfwmd.gov/", timeout=10)
        
        response = session.get(API_URL, params=params, timeout=30)
        
        # Debug: Save response to see what we're getting
        debug_file = f"debug_{structure}_response.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(f"Status: {response.status_code}\n")
            f.write(f"URL: {response.url}\n")
            f.write(f"Headers: {dict(response.headers)}\n")
            f.write(f"Response (first 500 chars):\n{response.text[:500]}\n")
        
        logger.debug(f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code != 200:
            logger.error(f"API returned status {response.status_code} for {structure}")
            logger.error(f"Response: {response.text[:200]}")
            return None
        
        # Try to parse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for {structure}: {e}")
            logger.error(f"Response text: {response.text[:200]}")
            return None
        
        # Parse the response
        if "timeSeriesResponse" in data and "timeSeries" in data["timeSeriesResponse"]:
            time_series_list = data["timeSeriesResponse"]["timeSeries"]
            
            # Look for the FLOW time series
            for time_series in time_series_list:
                if ("parameter" in time_series and 
                    "parameterName" in time_series["parameter"] and
                    time_series["parameter"]["parameterName"] == "FLOW"):
                    
                    # Found the flow data
                    if "values" in time_series and len(time_series["values"]) > 0:
                        # Get the most recent value
                        latest_value = time_series["values"][0]
                        if "value" in latest_value:
                            flow_value = latest_value["value"]
                            
                            # Check if it's valid (not the noDataValue)
                            no_data_value = time_series["parameter"].get("noDataValue", -99999.0)
                            if flow_value != no_data_value:
                                logger.info(f"Got flow for {structure}: {flow_value} cfs")
                                return float(flow_value)
        
        logger.warning(f"No valid flow data found for {structure}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error fetching data for {structure}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching flow for {structure}: {e}")
        return None

def get_flow_simple(structure):
    """Simpler version for testing"""
    try:
        params = {
            "format": "json",
            "sites": structure,
            "status": "A"
        }
        
        # Simple request
        response = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
        
        print(f"\nTesting {structure}:")
        print(f"Status: {response.status_code}")
        print(f"URL: {response.url}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            print(f"Response preview: {response.text[:200]}")
            
            # Check if it looks like JSON
            text = response.text.strip()
            if text.startswith('{') or text.startswith('['):
                try:
                    data = json.loads(text)
                    print("✓ Valid JSON!")
                    
                    # Save for inspection
                    with open(f"test_{structure}.json", "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"Saved to test_{structure}.json")
                    
                except json.JSONDecodeError as e:
                    print(f"✗ JSON decode error: {e}")
            else:
                print("✗ Not JSON")
                # Save as text
                with open(f"test_{structure}.txt", "w") as f:
                    f.write(response.text)
        else:
            print(f"✗ Error: {response.text[:100]}")
            
    except Exception as e:
        print(f"✗ Exception: {e}")
    
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

def test_all_structures():
    """Test all structures to see what the API returns"""
    print("Testing API for all structures...")
    print("=" * 60)
    
    for structure in STRUCTURES:
        get_flow_simple(structure)
        print("-" * 40)

def main():
    """Main monitoring function"""
    logger.info("Starting spillway monitor...")
    
    # Check if Pushover credentials are set
    if not os.environ.get("PUSHOVER_TOKEN") or not os.environ.get("PUSHOVER_USER"):
        logger.warning("Pushover credentials not found in environment")
        logger.warning("Notifications will not be sent")
    
    # First test to see what we get
    test_all_structures()
    
    # Then run actual monitoring
    check_structures()
    logger.info("Check completed")

if __name__ == "__main__":
    main()
