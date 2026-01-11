import requests
import json

structures = ["S44", "S41", "S155", "S40"]

for structure in structures:
    print(f"\n{'='*60}")
    print(f"Testing {structure}")
    print('='*60)
    
    # Test realtime endpoint
    print("\n1. Realtime endpoint:")
    url = "https://sitedetailsreport.sfwmd.gov/realtime"
    params = {"format": "json", "sites": structure, "status": "A"}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Response type: {type(data)}")
            if isinstance(data, list):
                print(f"List length: {len(data)}")
                if len(data) > 0:
                    print("First item keys:", list(data[0].keys()))
                    print("First item:", json.dumps(data[0], indent=2))
            else:
                print("Data keys:", list(data.keys()))
                print("Sample:", json.dumps(data, indent=2)[:500])
    except Exception as e:
        print(f"Error: {e}")
    
    # Test mdm endpoint
    print("\n2. MDM endpoint:")
    url = "https://sitedetailsreport.sfwmd.gov/mdm"
    params = {"site": structure}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Response type: {type(data)}")
            if isinstance(data, dict):
                print("Keys:", list(data.keys()))
                print("Sample:", json.dumps(data, indent=2)[:500])
            else:
                print("Data:", json.dumps(data, indent=2)[:500])
    except Exception as e:
        print(f"Error: {e}")
