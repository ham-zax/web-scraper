
# scraper.py
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

def extract_content(html):
    soup = BeautifulSoup(html, 'html5lib')
    
    for tag in soup(['header', 'footer', 'aside']):
        tag.decompose()

    main_content = soup.find('main') or soup.body
    return main_content.get_text(separator="\n", strip=True) if main_content else ""

async def scrape_url(session, url):
    try:
        html = await fetch_html(session, url)
        content = extract_content(html)
        return {"URL": url, "content": content}
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

async def scrape_from_file(links_file):
    data = []
    with open(links_file, 'r') as f:
        urls = f.read().splitlines()
    
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result:
                data.append(result)
                print(f"Scraped: {result['URL']}")
    
    return data

async def scrape_website(base_url, max_depth):
    visited = set()
    to_visit = [(base_url, 0)]
    data = []

    async with aiohttp.ClientSession() as session:
        while to_visit:
            current_batch = to_visit[:10]  # Process 10 URLs at a time
            to_visit = to_visit[10:]

            tasks = [process_url(session, url, depth, visited, data, to_visit, max_depth, base_url) for url, depth in current_batch]
            await asyncio.gather(*tasks)

    return data

async def process_url(session, url, depth, visited, data, to_visit, max_depth, base_url):
    if url in visited or depth > max_depth:
        return

    visited.add(url)
    print(f"Scraping: {url} (Depth: {depth})")

    result = await scrape_url(session, url)
    if result:
        data.append(result)

    if depth < max_depth:
        try:
            html = await fetch_html(session, url)
            links = extract_internal_links(base_url, html)
            for link in links:
                if link not in visited:
                    to_visit.append((link, depth + 1))
        except Exception as e:
            print(f"Error fetching links from {url}: {e}")

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

async def save_to_json(data, file_name="scraped_data.json"):
    with open(file_name, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    print(f"Data successfully saved to {file_name}")

async def main():
    config = await load_config()
    start_url = config['start_url']
    max_depth = config['max_depth']
    output_file = config['output_file']
    use_generated_links = config['use_generated_links']
    links_file = config['links_file']
    
    start_time = time.time()
    
    if use_generated_links:
        scraped_data = await scrape_from_file(links_file)
    else:
        scraped_data = await scrape_website(start_url, max_depth)
    
    await save_to_json(scraped_data, output_file)
    
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())