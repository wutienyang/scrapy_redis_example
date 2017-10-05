# -*- coding: utf-8 -*-
# Scrapy settings for example project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

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