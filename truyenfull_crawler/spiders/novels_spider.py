import codecs
import scrapy
from scrapy import signals
import json
import requests
from lxml import html
from lxml import etree

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

            # Get title, cover image, url in this page.
            titles = body.xpath('//h3[contains(@class, "truyen-title")]/a/text()')
            urls = body.xpath('//h3[contains(@class, "truyen-title")]/a/@href')
            cover_images = body.xpath('//div[contains(@class, "list-truyen")]//div[@data-classname="cover"]/@data-image')

            # text_infos save latest chapter of a novel.
            text_infos = []
            tex_info_nodes = body.xpath('//div[contains(@class, "text-info")]/div/a')
            for list_element in tex_info_nodes:
                texts = list_element.xpath('.//text()')
                text_infos.append("".join(texts))

            # Go to page of each novel to get other information.
            images = []
            authors = []
            categories = []
            sources = []
            status = []
            rates = []
            descriptions = []
            for url in urls:
                # Load html content of a novel.
                res = requests.get(url)
                while res.status_code != 200:
                    res = requests.get(url)
                page_content = html.fromstring(res.content)

                # Extract information.
                image = page_content.xpath('//div[contains(@class, "book")]/img/@src')
                if (len(image) > 0):
                    images.append(image)
                else:
                    images.append("")

                author = page_content.xpath('//a[contains(@itemprop, "author")]/text()')
                if (len(author) > 0):
                    authors.append(author[0])
                else:
                    authors.append("")

                category = ", ".join(page_content.xpath('//a[contains(@itemprop, "genre")]/text()'))
                categories.append(category)

                source = page_content.xpath('//span[contains(@class, "source")]/text()')
                if (len(source) > 0):
                    sources.append(source[0])
                else:
                    sources.append("")

                stat = page_content.xpath('//span[contains(@class, "text-primary") or contains(@class, "text-success")]/text()')
                if (len(stat) > 0):
                    status.append(stat[0])
                else:
                    status.append("")

                rate = page_content.xpath('//div[contains(@class, "rate-holder")]/@data-score')[0]
                rates.append(rate)

                desc = page_content.xpath('//div[contains(@class, "desc-text")]')
                description_text = ""
                if (len(desc) > 0):
                    for element in desc[0]:
                        description_text += etree.tostring(element, encoding='unicode')
                descriptions.append(description_text)

            for title, url, cover_image, text_info, image, author, category, source, stat, rate, desc in (zip(titles, urls, cover_images, text_infos, images, authors, categories, sources, status, rates, descriptions)):
                self.count += 1
                self.novels_list.append({ 
                    "index": self.count, 
                    "title": title, 
                    "url": url,
                    "cover_image": cover_image,
                    "text_info": text_info,
                    "image": image,
                    "author": author,
                    "category": category,
                    "source": source,
                    "status": stat,
                    "rate": rate,
                    "description": desc
                })

            self.page_crawled += 1
            if self.page_crawled == self.max_page:
                with codecs.open('novels_list.json', 'w', encoding='utf-8') as outfile:
                    json.dump(self.novels_list, outfile, ensure_ascii=False)
