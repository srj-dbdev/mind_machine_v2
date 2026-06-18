import requests

url = "https://www.reddit.com/r/artificial/top.json?t=day&limit=10"

headers = {
    "User-Agent": "MindMachineBot/1.0"
}

response = requests.get(url, headers=headers)

print(response.status_code)
print(response.text[:500])

