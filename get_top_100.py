import urllib.request
import json
import csv
from io import StringIO
url = "https://tranco-list.eu/download/J997p/1000"
response = urllib.request.urlopen(url)
data = response.read().decode('utf-8')
reader = csv.reader(StringIO(data))
domains = []
for row in reader:
    domains.append(row[1])
    if len(domains) >= 100:
        break

output = "    \"Top 100 Popular\": [\n"
for d in domains:
    output += f'        {{ name: "{d}", url: "https://{d}", icon: "globe" }},\n'
output += "    ]"
print(output)
