#!/usr/bin/env python3
"""
Simple test version of monitor
"""

import requests
import json

structures = ["S40", "S44", "S41", "S155"]

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json',
}

print("Testing SFWMD API for spillway flow data")
print("=" * 60)

for structure in structures:
    print(f"\nChecking {structure}...")
    
    url = "https://sitedetailsreport.sfwmd.gov/realtime"
    params = {
        "format": "json",
        "sites": structure,
        "status": "A"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  URL: {response.url}")
        
        if response.status_code == 200:
            # Check if it's JSON
            text = response.text.strip()
            if text.startswith('{') or text.startswith('['):
                try:
                    data = json.loads(text)
                    print(f"  ✓ Got JSON response")
                    
                    # Save for inspection
                    with open(f"api_{structure}.json", "w") as f:
                        json.dump(data, f, indent=2)
                    
                    # Try to find flow data
                    if isinstance(data, dict) and "timeSeriesResponse" in data:
                        print(f"  Found timeSeriesResponse structure")
                        # Look for flow data here...
                        
                except json.JSONDecodeError as e:
                    print(f"  ✗ JSON error: {e}")
                    with open(f"error_{structure}.txt", "w") as f:
                        f.write(response.text)
            else:
                print(f"  ✗ Not JSON: {text[:100]}")
                with open(f"not_json_{structure}.txt", "w") as f:
                    f.write(response.text)
        else:
            print(f"  ✗ HTTP error: {response.text[:100]}")
            
    except Exception as e:
        print(f"  ✗ Exception: {e}")
    
    print("-" * 40)

print("\nTest complete!")
