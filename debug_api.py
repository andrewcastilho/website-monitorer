import requests
import json

structures = ["S40", "S44", "S41", "S155"]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}

for structure in structures:
    print(f"\n{'='*60}")
    print(f"Testing {structure}")
    print('='*60)
    
    url = "https://sitedetailsreport.sfwmd.gov/realtime"
    params = {"format": "json", "sites": structure, "status": "A"}
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        # First try without headers
        print("\n1. Without headers:")
        r1 = requests.get(url, params=params, timeout=10)
        print(f"   Status: {r1.status_code}")
        print(f"   Content-Type: {r1.headers.get('content-type')}")
        print(f"   Response (first 100 chars): {r1.text[:100]}")
        
        # Then try with headers
        print("\n2. With headers:")
        r2 = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"   Status: {r2.status_code}")
        print(f"   Content-Type: {r2.headers.get('content-type')}")
        print(f"   Response (first 100 chars): {r2.text[:100]}")
        
        # Try to parse
        if r2.status_code == 200:
            try:
                data = json.loads(r2.text)
                print(f"   ✓ JSON parsed successfully")
                
                # Save to file
                with open(f"{structure}_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                print(f"   Saved to {structure}_response.json")
                
            except json.JSONDecodeError:
                print(f"   ✗ Not valid JSON")
                # Save raw response
                with open(f"{structure}_raw.txt", "w") as f:
                    f.write(r2.text)
                
    except Exception as e:
        print(f"Error: {e}")
