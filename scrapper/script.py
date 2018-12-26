import aiohttp
import asyncio
import async_timeout
from bs4 import BeautifulSoup
import csv
import json
import re
from urllib.parse import urlparse
import time
import xlwt


class Scraper:
    url: str
    root_domain: str
    domain: str
    search_pattern: str

    def __init__(self, url: str, search_pattern: str):
        self.url = url
        parsed_url = urlparse(url)
        self.root_domain = parsed_url.netloc
        self.domain = parsed_url.geturl()
        self.search_pattern = search_pattern

    @staticmethod
    async def soup_d(html):
        return BeautifulSoup(html, 'html.parser')

    async def fetch(self, session, url: str=''):
        url = url if url else self.url
        async with async_timeout.timeout(10):
            async with session.get(url) as response:
                return await response.text()

    async def match_path(self, path):
        pattern = re.compile(self.search_pattern)
        matching = pattern.match(path)
        if  matching is None:
            return False, None
        return True, matching

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

    # methods to override
    async def extract_content(self, html):
        soup = await self.soup_d(html)
        content_area = soup.find("div", {"class": "entry-content"})
        return content_area.text

    async def extract_title(self, html):
        soup = await self.soup_d(html)
        content_area = soup.find("h1", {"class": "entry-title"})
        return content_area.text

    async def write_to(self, extension: str, data: list):
        if not data:
            return
        if extension == 'json':
            with open(f'data.{extension}', 'w') as outfile:
                json.dump(
                    data, 
                    outfile, 
                    sort_keys=True, 
                    indent=4, 
                    ensure_ascii=False
                )
        if extension == 'csv':
            with open(f'data.{extension}', 'w') as outfile:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)

                writer.writeheader()
                for item in data:
                    writer.writerow(item)
        if extension == 'xls':
            wb = xlwt.Workbook(encoding='utf-8')
            ws = wb.add_sheet('data')

            # Sheet header, first row
            row_num = 0

            font_style = xlwt.XFStyle()
            font_style.font.bold = True

            columns = list(data[0].keys())
            print(columns)

            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num], font_style)

            font_style = xlwt.XFStyle()

            for row in data:
                row_num += 1
                row = list(row.values())
                print(row)
                for col_num in range(len(row)):
                    ws.write(row_num, col_num, row[col_num], font_style)
            wb.save(f'data.{extension}')

    async def run(self):
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            html = await self.fetch(session)
            paths = await self.extract_links(html)
            data = []
            for path in paths:
                print(path)
                post_html = await self.fetch(session, path)
                post_content = await self.extract_content(post_html)
                post_title = await self.extract_title(post_html)
                data.append(
                    {
                        'url': path,
                        'title': post_title,
                        'content': post_content[:500]
                    }
                )
            await self.write_to('json', data)
            await self.write_to('csv', data)
            await self.write_to('xls', data)
            print("Entire request took", time.time()-start_time, "seconds")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        Scraper(
            url='http://tim.blog',
            search_pattern=r'^/(?P<year>\d+){4}/(?P<month>\d+){2}/(?P<day>\d+){2}/(?P<slug>[\w-]+)/$'
        ).run()
    )
