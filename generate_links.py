# generate_links.py
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
import json
import time
import os
import sys

async def load_config(config_file="config.json"):
    try:
        with open(config_file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Config file '{config_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in config file '{config_file}'.")
        sys.exit(1)

async def fetch_html(session, url):
    try:
        async with session.get(url) as response:
            return await response.text()
    except aiohttp.ClientError as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_internal_links(base_url, html):
    if not html:
        return set()
    soup = BeautifulSoup(html, 'html5lib')
    links = set()
    base_domain = urlparse(base_url).netloc
    base_path = urlparse(base_url).path

    for anchor in soup.find_all('a', href=True):
        href = anchor['href']
        full_url = urljoin(base_url, href)
        defragged_url, _ = urldefrag(full_url)  # Remove the fragment
        parsed_url = urlparse(defragged_url)

        if parsed_url.netloc == base_domain and parsed_url.path.startswith(base_path):
            links.add(defragged_url)
    
    return links
async def generate_links(start_url, max_depth, output_file):
    visited = set()
    to_visit = [(start_url, 0)]
    all_links = set()

    # Load existing links
    try:
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                existing_links = set(f.read().splitlines())
            all_links.update(existing_links)
            visited.update(existing_links)
            print(f"Loaded {len(existing_links)} existing links.")
    except IOError as e:
        print(f"Warning: Could not read existing links file: {e}")

    async with aiohttp.ClientSession() as session:
        while to_visit:
            current_batch = to_visit[:10]  # Process 10 URLs at a time
            to_visit = to_visit[10:]

            tasks = [process_url(session, url, depth, visited, all_links, to_visit, max_depth, start_url) for url, depth in current_batch]
            await asyncio.gather(*tasks)

            # Update the file in real-time
            try:
                with open(output_file, 'w') as f:
                    for link in sorted(all_links):
                        f.write(f"{link}\n")
            except IOError as e:
                print(f"Error writing to output file: {e}")

    print(f"Generated links saved to {output_file}")
    print(f"Total unique links: {len(all_links)}")

async def process_url(session, url, depth, visited, all_links, to_visit, max_depth, start_url):
    if url in visited or depth > max_depth:
        return

    visited.add(url)
    all_links.add(url)
    print(f"Generating links from: {url} (Depth: {depth})")

    html = await fetch_html(session, url)
    if html:
        links = extract_internal_links(start_url, html)
        for link in links:
            if link not in visited:
                to_visit.append((link, depth + 1))

async def main():
    try:
        config = await load_config()
        start_url = config['start_url']
        max_depth = config['max_depth']
        links_file = config['links_file']

        start_time = time.time()
        await generate_links(start_url, max_depth, links_file)
        end_time = time.time()
        print(f"Total time taken: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())