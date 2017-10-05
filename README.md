# 目的
[Scrapy](https://scrapy.org/) 是一個強大通用型框架，但是資料一旦多了起來，就採用多機器進行加速爬取，但是 Scrapy不支持分散式，[Scrapy-Redis](https://github.com/rmax/scrapy-redis) 就因此而誕生，假設一個簡單的情形有100個 urls 會需要爬取，一個機器爬100次，兩個機器各爬50次，時間隨機器的增加而線性減少，我們只要可以有效地分配100個 urls 給多數機器就可以達到分散式爬取，Redis就是處理分配 urls 的任務。

網路上相關的介紹和原理非常多，但是詳細的實例卻很少或是常常有錯，因此本篇 blog 主要為介紹從零到一建出一個分散式爬取的簡單例子。

# 安裝Redis並測試遠端連線
a機器 ip: 10.2.0.10
b機器
兩台機器都需要安裝 Redis
`sudo apt install redis-server`

然後a機器需要設定外連ip 
`vim /etc/redis.conf` 
```
找到這行
#bind 127.0.0.1
修改為你自己的ip
bind 10.2.0.10
```
重啟 Redis 
`sudo /etc/init.d/redis-server restart`

b機器測試能不能連過去
`redis-cli -h 10.2.0.10`

如果出現，代表連線成功(6379是預設的port)
`10.2.0.10:6379>` 

# 實戰 (蘋果日報)
<img class="center" src="http://user-image.logdown.io/user/25406/blog/24396/post/2777588/99AISgoJRXSRHP6Z0md1_%E8%9E%A2%E5%B9%95%E5%BF%AB%E7%85%A7%202017-10-05%20%E4%B8%8B%E5%8D%881.04.54.png" alt="螢幕快照 2017-10-05 下午1.04.54.png">

url是 http://www.appledaily.com.tw/realtimenews/section/new/1 從1到10
要抓 list 的 title

<img class="center" src="http://user-image.logdown.io/user/25406/blog/24396/post/2777588/4BMjio23S8mc08WFpuyg_%E8%9E%A2%E5%B9%95%E5%BF%AB%E7%85%A7%202017-10-05%20%E4%B8%8B%E5%8D%881.05.28.png" alt="螢幕快照 2017-10-05 下午1.05.28.png">

也會進到內文中抓 content 的 title
總共抓取即時資訊的10頁，每一頁的標題和點進去標題後內文的標題

先安裝 scrapy 和 scrapy-redis
`pip install scrapy`
`pip install scrapy-redis`
scrapy 是一定要安裝的，scrapy-redis 則是改造了collection.deque，變成用redis來分配urls。
scrapy 不太好裝，不同OS和版本都會有不同問題，網路上資源也蠻多的但就要自己慢慢修好，裝起來也先跑跑看example，等到確定可以 work 再來以下的範例。

開始建立 scrapy project 下 `scrapy startproject apple`
進到剛建立好的 project `cd apple`
看一下結構 `tree`
![螢幕快照 2017-10-05 下午1.27.00.png](http://user-image.logdown.io/user/25406/blog/24396/post/2777588/hxrXQq5gRCGabaCDAW3L_%E8%9E%A2%E5%B9%95%E5%BF%AB%E7%85%A7%202017-10-05%20%E4%B8%8B%E5%8D%881.27.00.png)

以下修改的方式都是參考 [scrapy-redis](https://github.com/rmax/scrapy-redis) 的 example
python 版本皆為 2.7
首先编辑 settings 文件:：
``` python settings.py
# -*- coding: utf-8 -*-
# Scrapy settings for example project
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#     http://doc.scrapy.org/topics/settings.html
BOT_NAME = 'apple'
SPIDER_MODULES = ['apple.spiders']
NEWSPIDER_MODULE = 'apple.spiders'
USER_AGENT = 'scrapy-redis (+https://github.com/rolando/scrapy-redis)'
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
# SCHEDULER_PERSIST 設定是否中斷後會繼續下載 (測試的時候最好條為 False，不然抓一次抓完就不會跑了)
SCHEDULER_PERSIST = False
# 判斷從Redis取出urls時的方式 PriorityQueue, Queue, Stack
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderPriorityQueue"
#SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderQueue"
#SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderStack"
ITEM_PIPELINES = {
    'scrapy_redis.pipelines.RedisPipeline': 400
}
# 調整LOG的形式，可改為 INFO ERROR WARNING...
LOG_LEVEL = 'DEBUG'
# Introduce an artifical delay to make use of parallelism. to speed up the
# crawl.
# 設定延遲時間
DOWNLOAD_DELAY = 1
# Redis 的 ip (此範例為 a機器)
REDIS_HOST = '10.2.0.10'
REDIS_PORT = 6379
```

編輯 items:
``` python items.py
# Define here the models for your scraped items
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html
import scrapy
class AppleItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    title = scrapy.Field()
```
在 spiders 的資料夾中建立 apple.py ，爬蟲的主體
``` python apple.py
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
```
把 a機器的整個 project 複製到 b機器上
`scp -r apple/ user@b機器ip:your path/apple/`
分別進到兩機器
`cd apple`
執行 (兩台都要輸入這個指令)
`scrapy crawl apple`
這時兩個爬蟲都會啟動，呈現待機狀態，因為目前 Redis 沒有 url，因此要 push 進去
b機器執行把 url push 到 redis 中
`redis-cli -h 10.2.0.10 lpush apple http://appledaily.com.tw/realtimenews/section/new/`

然後就可以看到兩個爬蟲開始爬了，仔細看一下 print 的過程，會發現爬取的東西都不一樣就代表成功了！
或是要輸出 json 來驗證也可以
只要把指令改成
`scrapy crawl apple -o apple.json`
兩台機器存的內容也會不一樣，或是第一次開一台，第二次開兩台，把第兩次的檔案合併會等於第一次爬取的檔案內容。

# 結尾
##### 注意：
##### 1. RedisSpider 不需要寫 start_urls (很多教學寫分散式但是都沒用到這個 RedisSpider 有點傻眼，一般的 scrapy 是用這個 CrawlSpider，要啟用 Redis ，就要用 RedisSpider (apple.py裡面))
##### 2. 必須指定 redis_key (apple.py裡面)，爬蟲才會去讀取 Redis 這個 key 中存的值，並根據指令的 key ，由 redis-cli -h 10.2.0.10 lpush key start_urls。    
##### 3. 爬取的地方，我有點偷懶使用 BeautifulSoup ，官網就有直白的說 BeautifulSoup 就是慢，建議使用內建的 xpath, css selector...
    
附上 [Blog](http://wutienyang-blog.logdown.com/posts/2777588--scrapy-redis)
