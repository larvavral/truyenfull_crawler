import codecs
import scrapy
from scrapy import signals
import json
import requests
from lxml import html
from lxml import etree
from time import sleep
import urlparse
import os

class ChaptersSpider(scrapy.Spider):
    name = "chapters"
    start_urls = []

    @classmethod 
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(ChaptersSpider, cls).from_crawler(
            crawler, *args, **kwargs)
        crawler.signals.connect(
            spider.spider_opened, signal=signals.spider_opened)
        return spider

    def spider_opened(self, spider):
        # Load novels_list from json file, which is crawled by novels_spider.py.
        novels_list = []
        with codecs.open('novels_list.json', 'r', encoding='utf-8') as infile:
            novels_list = json.load(infile)
        # print(novels_list[0])
        # print(len(novels_list))

        # Initialize start_urls.
        for novel in novels_list:
            self.start_urls.append(novel['url'])

    def parse(self, response):
        # We will crawl from novel page to get all chapters content.

        if response.status == 200:
            body = html.fromstring(response.text)

            # Get all chapter urls of this novel.
            chapter_urls = []
            self.get_chapter_url(body, chapter_urls)

            # Get the content of chapters.
            chapters_list = []
            index = 0
            for url in chapter_urls:
                index += 1
                print(url)
                # path = urlparse.urlparse(url).path
                for x in url.split('/'):
                    if x != "":
                        path = x
                # print(path)

                # Send request to "truyenfull.vn" server to get pages.
                # Retry until request succeed.
                res = requests.get(url)
                while res.status_code != 200:
                    res = requests.get(url)
                    sleep(0.2)
                page_content = html.fromstring(res.content)

                text = page_content.xpath('//a[contains(@class, "chapter-title")]/descendant::text()')
                chapter_title = ' '.join(text)
                chapter_content = page_content.xpath('//div[contains(@class, "chapter-c")]')[0]

                content = ''
                for element in chapter_content:
                    content += etree.tostring(element, encoding='unicode')
                chapters_list.append({ "index": index, "title": chapter_title, "content": content, "path": path })

                # Need to sleep a little bit to avoid 503 error response from "truyenfull.vn" server.
                sleep(0.2)

            # Write all chapters content to file.
            dirname = os.path.dirname(response.url)
            novel_name = './chapters/' + dirname[dirname.rfind('/') + 1:] + '.json'
            with codecs.open(novel_name, 'w', encoding='utf-8') as outfile:
                json.dump(chapters_list, outfile, ensure_ascii=False)

    def get_chapter_num(self, body):
        # Get title of the last but one 'li' tag, in 'ul' with class is 'pagination'.
        title = body.xpath('//ul[contains(@class, "pagination")]/li[last()-1]/a/@title')

        chapter_num = 0
        # Find the pagination, get the latest chapter at the last page.
        if len(title) > 0:
            # Go to the last page by url.
            last_page_url = body.xpath('//ul[contains(@class, "pagination")]/li[last()-1]/a/@href')[0]
            last_page = html.fromstring(requests.get(last_page_url).content)
            
            # Get the latest chapter number.
            last_title = last_page.xpath('//ul[contains(@class, "list-chapter")]/li[last()]/a/@href')[0]
            chapter_num = int(last_title[last_title.rfind('-') + 1 - len(last_title):-1])
        # This novel just have 1 page, so we cannot find the pagination.
        else:
            # Get the latest chapter number.
            last_title = body.xpath('//ul[contains(@class, "list-chapter")]/li[last()]/a/@href')[0]
            chapter_num = int(last_title[last_title.rfind('-') + 1 - len(last_title):-1])

        return chapter_num

    def get_chapter_url(self, body, chapter_urls):
        # Chapters is paginated to many page. So we need recursive all pages to get all
        # chapter urls.
        urls = body.xpath('//ul[contains(@class, "list-chapter")]/li/a/@href')
        chapter_urls.extend(urls)

        # Recursive next page.
        next_page_url = body.xpath('//ul[contains(@class, "pagination")]/li[last()]/a/@href')
        if len(next_page_url) > 0:
            print(next_page_url[0])
            res = requests.get(next_page_url[0])
            while res.status_code != 200:
                res = requests.get(next_page_url[0])
                sleep(0.2)

            self.get_chapter_url(html.fromstring(res.content), chapter_urls)



