import aiohttp
import asyncio
import async_timeout
from bs4 import BeautifulSoup
from collections import Counter
import re
from urllib.parse import urlparse
import time


async def process_string(string):
    string = string.replace("\n", " ")
    string = string.replace("—", "")
    string = string.replace("|", "")
    string = string.replace("\n", " ")
    string = string.replace("\"", "")
    string = string.replace("\xa0", " ")
    string = string.replace("“", "")
    string = string.replace("”", "")
    string = string.replace("–", "")
    string = string.replace(".", "")
    string = string.replace("?", "")
    string = string.replace(",", "")
    string = string.replace("'ve", " have")
    #string = string.replace(".", " || PERIOD ||")
    #string = string.replace("?", " || QUESTION_MARK ||")
    return string.strip()


class Scraper:
    url: str
    root_domain: str
    domain: str
    content_area_class: str
    search_pattern: str

    def __init__(self, url: str, content_area_class: str, search_pattern: str):
        self.url = url
        parsed_url = urlparse(url)
        self.root_domain = parsed_url.netloc
        self.domain = parsed_url.geturl()
        self.content_area_class = content_area_class
        self.search_pattern = search_pattern

    @staticmethod
    async def soup_d(html):
        return BeautifulSoup(html, 'html.parser')

    async def match_path(self, path):
        pattern = re.compile(self.search_pattern)
        matching = pattern.match(path)
        if  matching is None:
            return False, None
        return True, matching

    async def fetch(self, session, url: str=''):
        url = url if url else self.url
        async with async_timeout.timeout(10):
            async with session.get(url) as response:
                return await response.text()

    async def extract_content(self, html):
        soup = await self.soup_d(html)
        content_area = soup.find("div", {"class": self.content_area_class})
        return content_area.text

    async def extract_links(self, html, local_only=True):
        soup = await self.soup_d(html)
        href_tags = soup.find_all("a", href=True)
        links = paths = [a['href'] for a in href_tags]
        if local_only:
            paths = []
            for link in links:
                parsed_url = urlparse(link)
                if parsed_url.netloc == self.root_domain:
                    path = parsed_url.path
                    is_matching = await self.match_path(path)
                    if is_matching[0]:
                        paths.append(f'{self.domain}{path}')
        return list(set(paths))

    async def run(self):
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            html = await self.fetch(session)
            paths = await self.extract_links(html)
            words = []
            for path in paths:
                print('post_url:', path)
                post_html = await self.fetch(session, path)
                post_content = await self.extract_content(post_html)
                string = await process_string(post_content)
                words += string.split()
            word_freq = Counter(words)
            print("Entire request took", time.time()-start_time, "seconds")
            print(word_freq.most_common(10))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        Scraper(
            url='http://tim.blog',
            content_area_class='entry-content',
            search_pattern=r'^/(?P<year>\d+){4}/(?P<month>\d+){2}/(?P<day>\d+){2}/(?P<slug>[\w-]+)/$'
        ).run()
    )
