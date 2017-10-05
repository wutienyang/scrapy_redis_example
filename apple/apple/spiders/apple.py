# -*- coding: utf-8 -*-
from scrapy_redis.spiders import RedisCrawlSpider
from ..items import AppleItem
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
import scrapy
from bs4 import BeautifulSoup

class AppleSpider(RedisCrawlSpider):
    name = 'apple'
    redis_key = 'apple'
    # LinkExtractor 可以給爬取urls制定規則，[1-10] 數字1,2,3...9,10
    rules = [Rule(LinkExtractor(allow=('/realtimenews/section/new/[1-10]$')),callback='parse_list',follow=True)]

    def parse_list(self, response):
        domain = 'http://www.appledaily.com.tw'
        res = BeautifulSoup(response.text)
        for news in res.select('.rtddt'):
            list_title = news.h1.string.encode('utf-8')
            print list_title
            # 傳入 list 的 url 給 parse_detail 去 parse content title
            yield scrapy.Request(domain + news.select('a')[0]['href'], self.parse_detail)

    def parse_detail(self, response):
        res = BeautifulSoup(response.text)
        content_title = res.find("h1", {"id": "h1"}).string.encode('utf-8')
        print content_title
        appleitem = AppleItem()
        appleitem['title'] = res.find("h1", {"id": "h1"}).string
        return appleitem