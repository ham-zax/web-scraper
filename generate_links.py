
# generate_links.py
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import time

async def load_config(config_file="config.json"):
    with open(config_file, 'r') as file:
        return json.load(file)

async def fetch_html(session, url):
    async with session.get(url) as response:
        return await response.text()

def extract_internal_links(base_url, html):
    soup = BeautifulSoup(html, 'html5lib')
    links = set()
    base_domain = urlparse(base_url).netloc

    for anchor in soup.find_all('a', href=True):
        href = anchor['href']
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)

        if parsed_url.netloc == base_domain and parsed_url.path.startswith(urlparse(base_url).path):
            links.add(full_url)
    
    return links

async def generate_links(start_url, max_depth, output_file):
    visited = set()
    to_visit = [(start_url, 0)]
    all_links = set()

    async with aiohttp.ClientSession() as session:
        while to_visit:
            current_batch = to_visit[:10]  # Process 10 URLs at a time
            to_visit = to_visit[10:]

            tasks = [process_url(session, url, depth, visited, all_links, to_visit, max_depth, start_url) for url, depth in current_batch]
            await asyncio.gather(*tasks)

            # Update the file in real-time
            with open(output_file, 'w') as f:
                for link in sorted(all_links):
                    f.write(f"{link}\n")

    print(f"Generated links saved to {output_file}")

async def process_url(session, url, depth, visited, all_links, to_visit, max_depth, start_url):
    if url in visited or depth > max_depth:
        return

    visited.add(url)
    all_links.add(url)
    print(f"Generating links from: {url} (Depth: {depth})")

    try:
        html = await fetch_html(session, url)
        links = extract_internal_links(start_url, html)
        
        for link in links:
            if link not in visited:
                to_visit.append((link, depth + 1))
    except Exception as e:
        print(f"Error fetching {url}: {e}")

async def main():
    config = await load_config()
    start_url = config['start_url']
    max_depth = config['max_depth']
    links_file = config['links_file']

    start_time = time.time()
    await generate_links(start_url, max_depth, links_file)
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())