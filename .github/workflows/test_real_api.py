import requests
import json

# Test the real API
url = "https://sitestatus.api.sfwmd.gov/v1/sitestatus/realtime"
params = {"format": "json", "sites": "S40", "status": "A"}

headers = {
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

print("Testing real API endpoint...")
response = requests.get(url, params=params, headers=headers, timeout=10)

print(f"Status: {response.status_code}")
print(f"URL: {response.url}")

if response.status_code == 200:
    try:
        data = response.json()
        print("✓ Success! Got JSON response")
        
        # Save it
        with open("test_response.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Saved to test_response.json")
        
        # Find flow data
        if "timeSeriesResponse" in data:
            for ts in data["timeSeriesResponse"]["timeSeries"]:
                if ts.get("parameter", {}).get("parameterName") == "FLOW":
                    flow_value = ts["values"][0]["value"]
                    print(f"Flow value: {flow_value} cfs")
                    break
        
    except json.JSONDecodeError:
        print("✗ Not valid JSON")
        print(f"Response: {response.text[:200]}")
else:
    print(f"✗ HTTP error: {response.status_code}")
    print(f"Error: {response.text[:100]}")
