import codecs
import scrapy
from scrapy import signals
import json
import requests
from lxml import html

url = 'https://truyenfull.vn/danh-sach/truyen-moi/'

class NovelsSpider(scrapy.Spider):
    name = "novels"
    start_urls = []

    # Count number of pages, which are crawled in the run time. 
    page_crawled = 0
    # List all novels title and url link to that novel's page.
    novels_list = []
    # Novel list count.
    count = 0

    @classmethod 
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(NovelsSpider, cls).from_crawler(
            crawler, *args, **kwargs)
        crawler.signals.connect(
            spider.spider_opened, signal=signals.spider_opened)
        return spider
    
    def spider_opened(self, spider):
        # Get the max page.
        page = requests.get(url)
        tree = html.fromstring(page.content)
        # Get title of the last but one 'li' tag, in 'ul' with class is 'pagination'.
        last_title = tree.xpath('//ul[contains(@class, "pagination")]/li[last()-1]/a/@title')[0]
        # Last number in the above title.
        self.max_page = int(last_title[last_title.rfind(' ') + 1 - len(last_title):])

        # Initialize start_urls.
        for index in range(self.max_page):
            self.start_urls.append(url + 'trang-' + str(index + 1) + '/')
            print(self.start_urls[index])

    def parse(self, response):
        if response.status == 200:
            body = html.fromstring(response.text)

            titles = body.xpath('//h3[contains(@class, "truyen-title")]/a/text()')
            urls = body.xpath('//h3[contains(@class, "truyen-title")]/a/@href')
            cover_images = body.xpath('//img[contains(@class, "cover")]/@src')
            for t, s in (zip(titles, urls)):
                self.count += 1
                self.novels_list.append({ "index": self.count, "title" : t, "url" : s })

            self.page_crawled += 1
            if self.page_crawled == self.max_page:
                with codecs.open('novels_list.json', 'w', encoding='utf-8') as outfile:
                    json.dump(self.novels_list, outfile, ensure_ascii=False)
