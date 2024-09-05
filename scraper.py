import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import time
import aiofiles

async def load_config(config_file="config.json"):
    async with aiofiles.open(config_file, 'r') as file:
        return json.loads(await file.read())

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
    async with aiofiles.open(links_file, 'r') as f:
        urls = await f.read()
    urls = urls.splitlines()
    
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        
    return [result for result in results if result]

async def scrape_website(base_url, max_depth, max_concurrent):
    visited = set()
    to_visit = [(base_url, 0)]
    data = []

    async with aiohttp.ClientSession() as session:
        while to_visit:
            current_batch = to_visit[:max_concurrent]
            to_visit = to_visit[max_concurrent:]

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

async def save_to_json_realtime(data, file_name="scraped_data.json", is_first=False):
    async with aiofiles.open(file_name, 'a', encoding='utf-8') as json_file:
        if not is_first:
            await json_file.write(',\n')
        await json_file.write(json.dumps(data, ensure_ascii=False, indent=2))
        
async def main():
    config = await load_config()
    start_url = config['start_url']
    max_depth = config['max_depth']
    output_file = config['output_file']
    use_generated_links = config['use_generated_links']
    links_file = config['links_file']
    
    start_time = time.time()
    max_concurrent = config.get('max_concurrent', 10)

    # Start the JSON array
    async with aiofiles.open(output_file, 'w') as f:
        await f.write('[\n')

    if use_generated_links:
        scraped_data = await scrape_from_file(links_file)
        for i, item in enumerate(scraped_data):
            await save_to_json_realtime(item, output_file, is_first=(i==0))
    else:
        data = await scrape_website(start_url, max_depth, max_concurrent)
        for i, item in enumerate(data):
            await save_to_json_realtime(item, output_file, is_first=(i==0))
    
    # Close the JSON array
    async with aiofiles.open(output_file, 'a') as f:
        await f.write('\n]')
    
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds")
    
if __name__ == "__main__":
    asyncio.run(main())