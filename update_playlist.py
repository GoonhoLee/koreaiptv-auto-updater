#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新GitHub仓库
KBS频道使用手动维护的认证参数
"""

import requests
import re
import time
import json
import os
import base64
from datetime import datetime
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 配置信息
GITHUB_USERNAME = "GoonhoLee"
STABLE_REPO_NAME = "korean-tv-static"
FULL_ACCESS_TOKEN = os.getenv('FULL_ACCESS_TOKEN')

# 电视台配置
CHANNELS = [
    {
        "name": "KBS1",
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=11&ch_type=globalList",
        "tvg_id": "KBS1.kr"
    },
    {
        "name": "KBS2", 
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=12&ch_type=globalList",
        "tvg_id": "KBS2.kr"
    },
    {
        "name": "KBS 24",
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=81&ch_type=globalList",
        "tvg_id": "KBS24.kr"
    },
    {
        "name": "MBN",
        "url": "https://www.mbn.co.kr/vod/onair",
        "tvg_id": "MBN.kr"
    },
    # 以下频道放在最后面
    {
        "name": "KBS DRAMA",
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N91&ch_type=globalList",
        "tvg_id": "KBSDRAMA.kr"
    },
    {
        "name": "KBS JOY",
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N92&ch_type=globalList",
        "tvg_id": "KBSJOY.kr"
    },
    {
        "name": "KBS STORY",
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N94&ch_type=globalList",
        "tvg_id": "KBSSTORY.kr"
    },
    {
        "name": "KBS LIFE",
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N93&ch_type=globalList",
        "tvg_id": "KBSLIFE.kr"
    }
]

# 静态频道列表（保持不变）
STATIC_CHANNELS = [
    '#EXTINF:-1 tvg-id="TVChosun.kr",TV Chosun (720p)',
    '#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on.cstv',
    'http://onair.cdn.tvchosun.com/origin1/_definst_/tvchosun_s1/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="TVChosun2.kr",TV Chosun 2 (720p)',
    '#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on2.cstv',
    'http://onair2.cdn.tvchosun.com/origin2/_definst_/tvchosun_s3/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="YTN.kr",YTN',
    'https://ytnlive.ytn.co.kr/ytn/_definst_/ytnlive_stream_20220426/medialist_9171188557012390620_hls.m3u8',
    '',
    '#EXTINF:-1 tvg-id="YonhapNews.kr" tvg-logo="https://kenpark76.github.io/logo/연합뉴스TV.png" group-title="🐉한국방송🦆",연합뉴스',
    'https://dvar4azmtmll0.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-6tpj7htwv2prd/master.m3u8?ads.device_did=%7BPSID%7D&ads.device_dnt=%7BTARGETOPT%7D&ads.app_domain=%7BAPP_DOMAIN%7D&ads.app_name=%7BAPP_NAME%7D',
    '',
    '#EXTINF:-1 tvg-id="YonhapNews.kr" tvg-logo="https://kenpark76.github.io/logo/연합뉴스TV.png" group-title="🐉한국방송🦆",연합뉴스',
    'https://tistory1.daumcdn.net/tistory/2864485/skin/images/CATV_216_AB271679.m3u8',
    '',
    '#EXTINF:-1 tvg-id="SBS.kr" group-title="🐉한국방송🦆",SBS',
    'http://koreatv.dothome.co.kr/sbs.php',
    '',
    '#EXTINF:-1 tvg-id="SBS.kr" group-title="🐉한국방송🦆",SBS',
    'http://110.42.54.62:8080/live/sbs.m3u8',
    '',
    '#EXTINF:-1 tvg-id="SBSJTV.kr" group-title="🐉한국방송🦆",SBS JTV (406p) [Not 24/7]',
    'http://61.85.197.53:1935/jtv_live/myStream/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="JTV.kr" group-title="🐉한국방송🦆",JTV',
    'https://tistory1.daumcdn.net/tistory/2864485/skin/images/Public_58.m3u8',
    '',
    '#EXTINF:-1 tvg-id="MBC.kr" group-title="🐉한국방송🦆",MBC',
    'http://koreatv.dothome.co.kr/mbc.php',
    '',
    '#EXTINF:-1 tvg-id="MBCJeju.kr" group-title="🐉한국방송🦆",MBC제주TV',
    'https://wowza.jejumbc.com/live/tv_jejumbc/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="MBCChuncheon.kr" group-title="🐉한국방송🦆",MBC춘천',
    'https://stream.chmbc.co.kr/TV/myStream/playlist.m3u8'
]

# KBS频道基础URL映射
KBS_BASE_URLS = {
    "KBS1": "https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8",
    "KBS2": "https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8",
    "KBS 24": "https://news24.gscdn.kbs.co.kr/news24-02/news24-02_hd.m3u8",
    "KBS DRAMA": "https://kbsndrama.gscdn.kbs.co.kr/kbsndrama-02/kbsndrama-02_sd.m3u8",
    "KBS JOY": "https://kbsnjoy.gscdn.kbs.co.kr/kbsnjoy-02/kbsnjoy-02_sd.m3u8",
    "KBS STORY": "https://kbsnw.gscdn.kbs.co.kr/kbsnw-02/kbsnw-02_sd.m3u8",
    "KBS LIFE": "https://kbsnlife.gscdn.kbs.co.kr/kbsnlife-02/kbsnlife-02_sd.m3u8"
}

# KBS频道认证参数（需要手动定期更新）
# 更新方法：访问KBS网站，等待广告结束，复制完整的m3u8 URL
KBS_AUTH_PARAMS = {
    # 这些参数会过期，需要定期手动更新
    "KBS1": {
        "Policy": "eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8xdHYuZ3NjZG4ua2JzLmNvLmtyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjU2Mzk3MjR9fX1dfQ__",
        "Signature": "DAa9OYHseeotVqKiKqBjmI~8VTC-iFHGWqdVoet7M8TGbb2Qb86r8cMKUFU5w3pY4-EogXBEn33E5FUElMkZumWokz9jLSEdpFst3aWuAXH-ayLuZahUe4dwuw8uj9fITpVZoWn5wk~a9YdgQ2goZ5L5ZHXgTRvG-xc1~F4-STvIEp1-7gFLaGkF58~B7E93srgOIzFnXlL1bUTbRvq6YGDnOtm5I17RQo~Qp~mludJlcge~Ax6KrnZYoNRSZjj24hpOokvv6JOeGegSMrVNvqQNdVzHHa7amtiSlbbuDzsz7GcTWOYCb5vdFTzDtGXjSFObE4e0gG9kyVlfzJhFAA__",
        "Key-Pair-Id": "APKAICDSGT3Y7IXGJ3TA"
    },
    "KBS2": {
        "Policy": "eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8ydHYuZ3NjZG4ua2JzLmNvLmtyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjU2Mzk4MTd9fX1dfQ__",
        "Signature": "IPXlitb6uXmRgDLsOYiGRWaec4~a0DJqahypbtf6jFYZdgvadI28euD~QKZwGOJmpa5FqQonMF1Lrcbfs-2EpoU5lEML~mHwE9Gxj1ws4EymA7XlzJwEdKTRGdBIYlCjIAvmF6I55oH5IGZYYCY~M4w37NFASZlv3NR0~XE1S9EJjKPQD5vX6sa-dsJiu53wNyBTQcqLBpv7Ibt9EvlrU3fTz3k-38VkC5MA4AgCZHjowQktDoYRBEDPAwbR6GEMAFjxSlCvAkxi5V8X-od4XWpIdx8d1gbzvutAHT9trMvF5LX2LzKLB0lVKMOteRjnEP6Z5YndYE3hdMEcgtOzlA__",
        "Key-Pair-Id": "APKAICDSGT3Y7IXGJ3TA"
    },
    "KBS 24": {
        "Policy": "eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9uZXdzMjQuZ3NjZG4ua2JzLmNvLmtyL25ld3MyNC0wMi8qIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzY1NjM5ODI5fX19XX0_",
        "Signature": "R7g6u7wWLRHVmrq4eZujwXHb0TlMlPkjBaNuSea0RYA-a7vcpiXmAHEXIIAtLPUHSMzhq5vFWbzaBLkDVVuXRNbhhoi3OxtvyP6CSq-cnjgwTrrp~9421oe1COVP6hZq~dtwDNgYR45WW3F7l28ayj0RW2CTp8cMzXB1GwRxBSHPk0CJYtwVwOPQ-vNl0rjZYPzVv5VcLOPJegg5dMSIKezRgADQJTMXWtxlivo3ltJEWFoc~KzlB5Wk5cNdyDzfEoIN6TVqtIitURhWtZiz1wpxE9GLTAsVX1fAEiRM67kDLjTyzCtY9niPMrAlwGiBgZvDaP~LdBH7O0m7-niujg__",
        "Key-Pair-Id": "APKAICDSGT3Y7IXGJ3TA"
    },
    "KBS DRAMA": {
        "Policy": "eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9rYnNuZHJhbWEuZ3NjZG4ua2JzLmNvLmtyL2tic25kcmFtYS0wMi8qIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzY1NjM5OTIzfX19XX0_",
        "Signature": "Kyozib4mqtgyMnvJQIo8DCluFK9uMAiNFGvT1hQP-CFRxZD7sWzBQC7tcGXAwdGg0ui71PmOcGVzZY35~m8mnPxbh3nP4F0mRtlBYEjDIIY5mPybMwk~CfwcsfIwj4OlO1F6Ktkd2GemtsjEm47FMEUA1rcMX4yKMFEG5RV7MI0~TzAJFOGeVjK1Nw2Q6LF9noCoXlUDrhEL6sh8J8sRFtOt2Si4dPoVybZDtEsKyGzgH0v4rBAXetvpy5dzyUIgD1jk36PKVgH8WfDKKMRZaZs9ZdCzvvTiA5c-OFUSmw1ig6FG5kUPbsrVif8LN7xAGfBAgJo9B882Uy0rh66qow__",
        "Key-Pair-Id": "APKAICDSGT3Y7IXGJ3TA"
    },
    "KBS JOY": {
        "Policy": "eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9rYnNuam95LmdzY2RuLmticy5jby5rci9rYnNuam95LTAyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjU2Mzk5NTN9fX1dfQ__",
        "Signature": "lbEQuwhlaHAasRkrNWn0T1uTaJ3Ez61n7Kijzz7eHDXYdXzCWr8QCYHEBaYOgqBvYazqPqkldxPgMhg~IzyC9XN6t8o2ETgN83tZN6JtplVn7aYISYXg95UpBSoRV5Dhp21Mgmy7M~bWo1mKcKeoRH4nzkrl0mejLZ7cXlNu9sena-l42pXYKrI7X2cEF7mumV3NooRdTvolLYvUjFfj65UL9IZymsEtHwBmkk3nDCf8NXYwTIX9f1AT281Unxo92vtmKcJGzaIuoajNgkMJ3jE9lERoOGMnPc7pn11Y~j9kaO6rO3ht8c60mQaXX9Q0DXowAXw3KkIjS9SVWxjVNQ__",
        "Key-Pair-Id": "APKAICDSGT3Y7IXGJ3TA"
    },
    "KBS STORY": {
        "Policy": "eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9rYnNudy5nc2Nkbi5rYnMuY28ua3Iva2JzbnctMDIvKiIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2NTY0MDA2M319fV19",
        "Signature": "g8JjSuy~TnERV8F341xDUhh1FX1WIB7ehrH7nvOBnBrj8vOeiLYicghIN9Fys9zmeURyFQRGGmokYx8Mwaq~8GCKdGjCRGwOi97YWdtUoO2DF0-IxSyYNElSrVru3DNe0jGABS6bXU4nGM~NLD8PzZbn0eIdXQQBT1OJ04N6c~OSahcks5RV-moCk4FojIYRJ92tIYQJqmDzfvFRLNiTV3VUhVRz-ZCRBxNLBWnqvq20l5RSYB1dzoW-Ixpnz5-8k0p5iui9zqmoCU6~-eXL0omMYRwVIXHsuI6jGGvBv3RCjnxV03wyPd--WWQ4ikIr7T2KBut389dUnpTM7qQgqg__",
        "Key-Pair-Id": "APKAICDSGT3Y7IXGJ3TA"
    },
    "KBS LIFE": {
        "Policy": "eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9rYnNubGlmZS5nc2Nkbi5rYnMuY28ua3Iva2JzbmxpZmUtMDIvKiIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2NTY0MDA2MX19fV19",
        "Signature": "Dxvfd8XU3PobVd-rZwznN2UjfhGYYCDwwi1t8515Rt1dDsLm10oRJ65GAd0WCEbjiqpyMmr51cCClaFc9SWkhFGCxfUFc0UIxVsluuFj8PGLrAVuwuqmODmjlqvR6lYwbMXEQA8Kdc-LHAEsnMKdoeumIi0g8iQ2~ocyDs-5ZX4~41mVmNjVaphXHK5x4rHhosNSK3RNlHU28dTI8s3jYED51QtUt3xJ8L-LlXGXwwAjPS6zRMksnisrlQRvGVjxfGHy9dtT~SejMOEElKMF6WNsZur69ZLTNXdw4l~XN0MNY4reNHbryVV2x8rOkvxztq1OUwLDufH8vNgB7xCCPg__",
        "Key-Pair-Id": "APKAICDSGT3Y7IXGJ3TA"
    }
}

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_kbs_m3u8_with_auth(channel_name):
    """获取带认证参数的KBS m3u8 URL"""
    try:
        print(f"🎬 正在获取 {channel_name}...")
        
        if channel_name not in KBS_BASE_URLS:
            print(f"❌ 未知的KBS频道: {channel_name}")
            return None
        
        base_url = KBS_BASE_URLS[channel_name]
        
        # 检查是否有认证参数
        if channel_name in KBS_AUTH_PARAMS:
            params = KBS_AUTH_PARAMS[channel_name]
            policy = params.get("Policy")
            signature = params.get("Signature")
            key_pair_id = params.get("Key-Pair-Id", "APKAICDSGT3Y7IXGJ3TA")
            
            if policy and signature:
                # 构建完整的认证URL
                auth_url = f"{base_url}?Policy={policy}&Key-Pair-Id={key_pair_id}&Signature={signature}"
                print(f"✅ 使用预定义认证参数: {channel_name}")
                print(f"🔗 URL长度: {len(auth_url)} 字符")
                return auth_url
            else:
                print(f"⚠️  {channel_name} 的认证参数不完整，使用基础URL")
        else:
            print(f"⚠️  未找到 {channel_name} 的认证参数，使用基础URL")
        
        # 返回基础URL
        print(f"📋 使用基础URL: {channel_name}")
        return base_url
        
    except Exception as e:
        print(f"❌ 获取 {channel_name} 时出错: {str(e)}")
        return None

def get_real_mbn_url_from_response(auth_url):
    """从MBN认证链接的响应内容获取真实m3u8地址"""
    try:
        print(f"🔗 请求MBN认证链接: {auth_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.mbn.co.kr/vod/onair'
        }
        
        response = requests.get(auth_url, headers=headers, timeout=(5, 10))
        
        if response.status_code == 200:
            content = response.text.strip()
            
            if content.startswith('http') and '.m3u8' in content and 'hls-live.mbn.co.kr' in content:
                print(f"✅ 获取到MBN地址: {content}")
                return content
            else:
                print(f"❌ 响应内容不是有效的m3u8 URL: {content}")
                return None
        else:
            print(f"❌ 认证链接请求失败，状态码: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 请求MBN认证链接时出错: {str(e)}")
        return None

def get_mbn_m3u8_multiple_quality(driver):
    """获取MBN的m3u8链接 - 同时获取1000k和600k版本"""
    mbn_channels = []
    
    try:
        print("🚀 正在获取 MBN 多画质版本...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        time.sleep(15)
        
        m3u8_urls = []
        target_domains = ['mbn.co.kr', 'hls-live.mbn.co.kr']
        
        # 网络请求监控
        try:
            logs = driver.get_log('performance')
            for log in logs:
                try:
                    message = json.loads(log['message'])['message']
                    method = message.get('method')
                    
                    if method in ['Network.responseReceived', 'Network.requestWillBeSent']:
                        request = message['params'].get('request', {})
                        response = message['params'].get('response', {})
                        
                        urls = [request.get('url', ''), response.get('url', '')]
                        for url in urls:
                            if url and '.m3u8' in url and any(domain in url for domain in target_domains):
                                m3u8_urls.append(url)
                                
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️ 读取网络日志时出错: {e}")
        
        # 查找认证代理链接
        auth_urls = [url for url in m3u8_urls if 'mbnStreamAuth' in url]
        
        # 分别处理1000k和600k版本
        quality_configs = [
            {
                'quality': '1000k',
                'name': 'MBN（高画质）',
                'tvg_id': 'MBN.kr',
                'auth_urls': [url for url in auth_urls if '1000k' in url],
                'base_url': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8',
                'backup_url': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8'
            },
            {
                'quality': '600k',
                'name': 'MBN（标清）',
                'tvg_id': 'MBN.kr',
                'auth_urls': [url for url in auth_urls if '600k' in url],
                'base_url': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8',
                'backup_url': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8'
            }
        ]
        
        for config in quality_configs:
            print(f"\n🎯 正在获取 {config['quality']} 版本...")
            
            real_url = None
            
            # 首先尝试自动发现的认证链接
            if config['auth_urls']:
                print(f"🔍 找到 {config['quality']} 认证链接: {config['auth_urls'][0]}")
                real_url = get_real_mbn_url_from_response(config['auth_urls'][0])
                if real_url:
                    print(f"✅ 成功获取 {config['quality']} 版本")
                else:
                    print(f"❌ 自动发现的 {config['quality']} 认证链接无效")
            
            # 如果自动发现的链接失败，尝试构造认证链接
            if not real_url:
                print(f"🔄 尝试构造 {config['quality']} 认证链接...")
                constructed_auth_url = f"https://www.mbn.co.kr/player/mbnStreamAuth_new_live.mbn?vod_url={config['base_url']}"
                
                real_url = get_real_mbn_url_from_response(constructed_auth_url)
                if real_url:
                    print(f"✅ 通过构造链接获取 {config['quality']} 版本")
                else:
                    print(f"❌ 构造链接也失败，使用备用地址")
                    real_url = config['backup_url']
            
            # 添加到频道列表
            if real_url:
                mbn_channels.append({
                    'name': config['name'],
                    'tvg_id': config['tvg_id'],
                    'url': real_url,
                    'quality': config['quality']
                })
        
        # 如果两个版本都获取成功
        if len(mbn_channels) == 2:
            print("🎉 成功获取MBN双画质版本！")
        elif len(mbn_channels) == 1:
            print(f"⚠️ 只成功获取 {mbn_channels[0]['quality']} 版本")
        else:
            print("❌ 未能获取任何MBN版本，使用备用地址")
            mbn_channels.append({
                'name': 'MBN（高画质）',
                'tvg_id': 'MBN.kr',
                'url': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8',
                'quality': '1000k'
            })
            mbn_channels.append({
                'name': 'MBN（标清）',
                'tvg_id': 'MBN.kr',
                'url': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8',
                'quality': '600k'
            })
            
        return mbn_channels
            
    except Exception as e:
        print(f"❌ 获取 MBN 多画质版本时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        # 返回备用地址
        return [
            {
                'name': 'MBN（高画质）',
                'tvg_id': 'MBN.kr',
                'url': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8',
                'quality': '1000k'
            },
            {
                'name': 'MBN（标清）',
                'tvg_id': 'MBN.kr',
                'url': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8',
                'quality': '600k'
            }
        ]

def update_stable_repository(content):
    """更新GitHub固定仓库的M3U文件"""
    if not FULL_ACCESS_TOKEN:
        print("❌ 未找到FULL_ACCESS_TOKEN，跳过GitHub仓库更新")
        return False
        
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/contents/korean_tv.m3u"
    headers = {
        "Authorization": f"token {FULL_ACCESS_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # 获取文件当前SHA
        response = requests.get(url, headers=headers)
        sha = None
        if response.status_code == 200:
            sha = response.json().get('sha')
            print("📁 找到GitHub现有文件，准备更新...")
        else:
            print("📁 GitHub未找到现有文件，将创建新文件...")
        
        # Base64编码
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('ascii')
        
        # 更新或创建文件
        data = {
            "message": f"自动更新播放列表 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_base64,
            "committer": {
                "name": "GitHub Action",
                "email": "action@github.com"
            }
        }
        
        if sha:
            data["sha"] = sha
        
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code in [200, 201]:
            print("🎉 GitHub仓库更新成功!")
            github_static_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/main/korean_tv.m3u"
            print(f"🔗 GitHub静态URL: {github_static_url}")
            return True
        else:
            print(f"❌ GitHub仓库更新失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 更新GitHub仓库时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def generate_playlist(dynamic_channels):
    """生成完整的M3U播放列表"""
    lines = ["#EXTM3U"]
    lines.append(f"# 自动生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 分离出要放在后面的频道
    later_channels = ['KBS DRAMA', 'KBS JOY', 'KBS STORY', 'KBS LIFE']
    
    # 先添加其他动态频道
    for channel in dynamic_channels:
        if channel.get('url') and channel['name'] not in later_channels:
            lines.append(f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}",{channel["name"]}')
            lines.append(channel['url'])
            lines.append("")
    
    # 添加静态频道
    lines.extend(STATIC_CHANNELS)
    lines.append("")
    
    # 最后添加指定的KBS频道
    for channel in dynamic_channels:
        if channel.get('url') and channel['name'] in later_channels:
            lines.append(f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}",{channel["name"]}')
            lines.append(channel['url'])
            lines.append("")
    
    return "\n".join(lines)

def main():
    """主函数"""
    start_time = time.time()
    print("🎬 开始获取M3U8链接...")
    print(f"📺 计划获取 {len(CHANNELS)} 个频道")
    
    driver = None
    try:
        driver = setup_driver()
        dynamic_channels = []
        
        # 遍历所有频道进行抓取
        for channel in CHANNELS:
            print(f"\n{'='*50}")
            print(f"🔍 正在处理频道: {channel['name']}")
            
            if channel['name'] == "MBN":  # 精确匹配MBN
                # MBN特殊处理 - 多画质版本
                mbn_channels = get_mbn_m3u8_multiple_quality(driver)
                dynamic_channels.extend(mbn_channels)
                print(f"✅ {channel['name']} - 获取成功（双画质）")
                continue  # 跳过MBN的常规处理
            else:
                # KBS频道统一处理 - 使用预定义的认证参数
                try:
                    m3u8_url = get_kbs_m3u8_with_auth(channel['name'])
                    if m3u8_url:
                        dynamic_channels.append({
                            'name': channel['name'],
                            'tvg_id': channel['tvg_id'],
                            'url': m3u8_url
                        })
                        print(f"✅ {channel['name']} - 获取成功")
                    else:
                        print(f"❌ {channel['name']} - 获取失败")
                except Exception as e:
                    print(f"❌ 处理频道 {channel['name']} 时出错: {str(e)}")
                    continue
        
        print(f"\n{'='*50}")
        # 生成标准版播放列表
        standard_playlist = generate_playlist(dynamic_channels)
        print("✅ 播放列表生成完成!")

        # 更新GitHub仓库
        update_stable_repository(standard_playlist)

        # 保存到本地文件
        with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
            f.write(standard_playlist)

        print("💾 播放列表已保存:")
        print("  📁 korean_tv.m3u - 标准版")
        
        # 打印统计
        successful_channels = [ch for ch in dynamic_channels if ch.get('url')]
        print(f"📊 成功获取 {len(successful_channels)}/{len(dynamic_channels)} 个频道")
        
        # 显示频道信息
        print("\n🎯 成功频道列表:")
        for channel in successful_channels:
            print(f"  ✅ {channel['name']}")
        
    except Exception as e:
        print(f"❌ 执行过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            try:
                print("🔚 关闭浏览器驱动...")
                driver.quit()
            except Exception as e:
                print(f"⚠️ 关闭浏览器驱动时出现警告: {e}")
        
        # 计算总执行时间
        end_time = time.time()
        total_time = end_time - start_time
        print(f"⏱️ 总执行时间: {total_time:.2f}秒")

if __name__ == "__main__":
    main()
