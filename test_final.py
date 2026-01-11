import requests
import json

structure = "S40"
url = "https://sitedetailsreport.sfwmd.gov/realtime"
params = {"format": "json", "sites": structure, "status": "A"}

response = requests.get(url, params=params)
data = response.json()

# Find flow data
for time_series in data["timeSeriesResponse"]["timeSeries"]:
    if time_series["parameter"]["parameterName"] == "FLOW":
        flow_value = time_series["values"][0]["value"]
        print(f"Flow for {structure}: {flow_value} cfs")
        break
