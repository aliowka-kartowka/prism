import json
import re

html_path = '/Users/manun/workspace/prism/free_vpn/index.html.local'

with open(html_path, 'r') as f:
    content = f.read()

# Extract Top 100 block
top_100_match = re.search(r'"Top 100 Popular": \[(.*?)\]', content, re.DOTALL)
if not top_100_match:
    print("Top 100 Popular not found!")
    exit(1)

items_str = top_100_match.group(1)
items = re.findall(r'\{ name: "(.*?)", url: "(.*?)", icon: "(.*?)" \}', items_str)

categories = {
    "Search & Information": [],
    "Social Media": [],
    "Video & Streaming": [],
    "E-Commerce & Retail": [],
    "News & Media": [],
    "Business & Finance": [],
    "Technology & Tools": [],
    "Travel & Real Estate": [],
    "Adult Content": []
}

for name, url, icon in items:
    name_l = name.lower()
    
    # Assign specific icons and map categories
    if name_l in ['google', 'bing', 'yahoo', 'baidu', 'yandex', 'duckduckgo', 'naver', 'coccoc', 'sogou', 'sohu', 'wikipedia', 'fandom', 'quora']:
        icon = 'search' if name_l in ['google', 'bing', 'yahoo', 'baidu', 'duckduckgo', 'naver'] else 'book'
        categories['Search & Information'].append((name, url, icon))
    elif name_l in ['facebook', 'instagram', 'twitter', 'x', 'reddit', 'linkedin', 'tiktok', 'discord', 't', 'badoo', 'snapchat', 'pinterest', 'vk', 'weibo']:
        icon = 'users'
        categories['Social Media'].append((name, url, icon))
    elif name_l in ['youtube', 'netflix', 'twitch', 'hulu', 'vimeo', 'dailymotion', 'bilibili', 'zhanqi', 'max', 'disney', 'spotify', 'soundcloud', 'pandora', 'roblox']:
        icon = 'tv' if name_l not in ['spotify', 'soundcloud', 'pandora'] else 'music'
        categories["Video & Streaming"].append((name, url, icon))
    elif name_l in ['amazon', 'aliexpress', 'ebay', 'walmart', 'target', 'bestbuy', 'homedepot', 'lowes', 'etsy', 'wayfair']:
        icon = 'shopping-cart'
        categories['E-Commerce & Retail'].append((name, url, icon))
    elif name_l in ['cnn', 'bbc', 'nytimes', 'foxnews', 'washingtonpost', 'forbes', 'businessinsider', 'bloomberg', 'wsj', 'huffpost', 'cnbc', 'weather', 'accuweather']:
        icon = 'file-text'
        categories['News & Media'].append((name, url, icon))
    elif name_l in ['paypal', 'chase', 'wellsfargo', 'capitalone', 'bankofamerica']:
        icon = 'dollar-sign'
        categories['Business & Finance'].append((name, url, icon))
    elif name_l in ['microsoft', 'apple', 'samsung', 'github', 'chatgpt', 'zoom', 'office', 'adobe', 'wordpress', 'canva', 'speedtest', 'imgur', 'flickr', 'ups', 'fedex', 'usps']:
        icon = 'cpu'
        categories['Technology & Tools'].append((name, url, icon))
    elif name_l in ['booking', 'tripadvisor', 'yelp', 'zillow', 'craigslist', 'indeed']:
        icon = 'map-pin'
        categories['Travel & Real Estate'].append((name, url, icon))
    elif name_l in ['pornhub', 'xvideos', 'xhamster', 'xnxx', 'live', 'onlyfans', 'youporn']:
        icon = 'alert-triangle'
        categories['Adult Content'].append((name, url, icon))
    else:
        # fallback
        icon = 'globe'
        categories['Search & Information'].append((name, url, icon))

# Generate new category JS
new_cats = []
for cat, sites in categories.items():
    if len(sites) == 0: continue
    cat_str = f'    "{cat}": [\n'
    site_lines = []
    for name, url, icon in sites:
        site_lines.append(f'        {{ name: "{name}", url: "{url}", icon: "{icon}" }}')
    cat_str += ',\n'.join(site_lines) + '\n    ]'
    new_cats.append(cat_str)

new_code = ',\n'.join(new_cats) + '\n'

content = content[:top_100_match.start()] + new_code + content[top_100_match.end()+1:]

with open(html_path, 'w') as f:
    f.write(content)

print("Categorization complete.")
