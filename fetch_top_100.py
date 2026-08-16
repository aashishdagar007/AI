import json
import urllib.request
import time

repos = []
base_url = "https://api.github.com/search/repositories?q=hyperspectral&sort=stars&order=desc&per_page=100"

# Fetch first page
url = base_url
headers = {"User-Agent": "Python-HSI-Analysis"}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=30) as response:
    data = json.load(response)
    items = data.get("items", [])
    print(f"Page 1: {len(items)} repos fetched")
    repos.extend(items)
    print(f"Total so far: {len(repos)}")

# We got 100 in first page, that should be enough for top 100
if len(repos) >= 100:
    print(f"\nGot top {len(repos)} repos from first page")
else:
    print(f"Only got {len(repos)}, need more pages")
    # Fetch remaining pages
    for page in range(2, 6):
        time.sleep(2)
        page_url = f"https://api.github.com/search/repositories?q=hyperspectral&sort=stars&order=desc&per_page=100&page={page}"
        req = urllib.request.Request(page_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.load(response)
            items = data.get("items", [])
            print(f"Page {page}: {len(items)} repos")
            repos.extend(items)
            print(f"Total so far: {len(repos)}")
            if len(repos) >= 100:
                break

# Save to file for later use
with open("top_100_hsi_repos.json", "w") as f:
    json.dump(repos, f)

print(f"\nSaved {len(repos)} repos to top_100_hsi_repos.json")
print(f"\nTop 10 repos:")
for i, repo in enumerate(repos[:10]):
    print(f"  {i+1}. {repo['full_name']} - {repo['stargazers_count']} stars")
PYEOF