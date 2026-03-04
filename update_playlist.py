#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新GitHub仓库
全自动方案 - 深度分析KBS页面获取认证参数
"""

import requests
import re
import time
import json
import os
import base64
from datetime import datetime
from typing import Optional, Dict, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    'https://onaircdn.tvchosun.com/origin1/_definst_/tvchosun_s3/chunklist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="TVChosun2.kr",TV Chosun 2 (720p)',
    '#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on2.cstv',
    'https://onair2cdn.tvchosun.com/origin2/_definst_/tvchosun_s1/chunklist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="YTN.kr",YTN',
    'https://ytnlive.ytn.co.kr/ytn/_definst_/ytnlive_stream_20220426/medialist_9171188557012390620_hls.m3u8',
    '',
    '#EXTINF:-1 tvg-id="YonhapNews.kr" tvg-logo="https://kenpark76.github.io/logo/연합뉴스TV.png" group-title="🐉한국방송🦆",연합뉴스',
    'https://dvar4azmtmll0.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-6tpj7htwv2prd/master.m3u8?ads.device_did=%7BPSID%7D&ads.device_dnt=%7BTARGETOPT%7D&ads.app_domain=%7BAPP_DOMAIN%7D&ads.app_name=%7BAPP_NAME%7D',
    '',
    '#EXTINF:-1 tvg-id="SBS.kr" group-title="🐉한국방송🦆",SBS',
    'http://koreatv.dothome.co.kr/sbs.php',
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

# KBS频道基础URL映射（备用）
KBS_BASE_URLS = {
    "KBS1": "https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8",
    "KBS2": "https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8",
    "KBS 24": "https://news24.gscdn.kbs.co.kr/news24-02/news24-02_hd.m3u8",
    "KBS DRAMA": "https://kbsndrama.gscdn.kbs.co.kr/kbsndrama-02/kbsndrama-02_sd.m3u8",
    "KBS JOY": "https://kbsnjoy.gscdn.kbs.co.kr/kbsnjoy-02/kbsnjoy-02_sd.m3u8",
    "KBS STORY": "https://kbsnw.gscdn.kbs.co.kr/kbsnw-02/kbsnw-02_sd.m3u8",
    "KBS LIFE": "https://kbsnlife.gscdn.kbs.co.kr/kbsnlife-02/kbsnlife-02_sd.m3u8"
}

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 添加更多选项以模拟真实浏览器
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    
    # 启用性能日志
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 执行JavaScript来隐藏自动化特征
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def extract_m3u8_from_network_logs(driver, target_domains=None):
    """从网络日志中提取m3u8链接"""
    m3u8_urls = []
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
                        if url and '.m3u8' in url:
                            if target_domains:
                                if any(domain in url for domain in target_domains):
                                    m3u8_urls.append(url)
                            else:
                                m3u8_urls.append(url)
                            
            except Exception:
                continue
                
    except Exception as e:
        print(f"⚠️ 读取网络日志时出错: {e}")
    
    return list(set(m3u8_urls))

def deep_analyze_kbs_page(driver, channel_name):
    """深度分析KBS页面，寻找认证参数（后备方法）"""
    print(f"🔍 深度分析 {channel_name} 页面...")
    
    try:
        # 方法1: 直接搜索页面中的所有m3u8链接
        page_source = driver.page_source
        
        # 使用多种模式搜索
        patterns = [
            # 完整URL模式
            r'(https?://[^\s"\']*\.m3u8\?[^\s"\']*Policy=[^\s"\']*Signature=[^\s"\']*)',
            r'["\'](https?://[^"\']*\.m3u8\?[^"\']*Policy=[^"\']*Signature=[^"\']*)["\']',
            # 参数模式
            r'Policy=([A-Za-z0-9_\-~]+)',
            r'Signature=([A-Za-z0-9_\-~]+)',
            # JSON数据模式
            r'"url"\s*:\s*"([^"]*\.m3u8[^"]*)"',
            r'"src"\s*:\s*"([^"]*\.m3u8[^"]*)"',
            r'"streamUrl"\s*:\s*"([^"]*\.m3u8[^"]*)"',
            r'"source"\s*:\s*"([^"]*\.m3u8[^"]*)"',
        ]
        
        found_urls = []
        
        for pattern in patterns:
            matches = re.findall(pattern, page_source)
            for match in matches:
                if isinstance(match, str) and '.m3u8' in match:
                    if 'gscdn.kbs.co.kr' in match and 'Policy=' in match and 'Signature=' in match:
                        found_urls.append(match)
                        print(f"✅ 从页面找到认证URL: {match[:100]}...")
        
        if found_urls:
            return found_urls[0]
        
        # 方法2: 执行JavaScript获取播放器配置
        print("💻 执行JavaScript获取播放器数据...")
        js_scripts = [
            # 获取所有可能的视频源
            """
            var sources = [];
            // 获取video元素
            var videos = document.querySelectorAll('video');
            videos.forEach(v => {
                if (v.src) sources.push(v.src);
                if (v.currentSrc) sources.push(v.currentSrc);
            });
            
            // 获取source元素
            var sourceElements = document.querySelectorAll('source');
            sourceElements.forEach(s => {
                if (s.src) sources.push(s.src);
            });
            
            // 获取iframe内的video
            var iframes = document.querySelectorAll('iframe');
            iframes.forEach(iframe => {
                try {
                    var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    var iframeVideos = iframeDoc.querySelectorAll('video');
                    iframeVideos.forEach(v => {
                        if (v.src) sources.push(v.src);
                    });
                } catch(e) {}
            });
            
            return sources.filter(s => s.includes('.m3u8') && s.includes('kbs'));
            """,
            
            # 搜索全局变量中的视频配置
            """
            var configs = [];
            var keys = Object.keys(window);
            for (var i = 0; i < keys.length; i++) {
                var key = keys[i];
                try {
                    var value = window[key];
                    if (typeof value === 'string' && value.includes('.m3u8') && value.includes('gscdn.kbs.co.kr')) {
                        configs.push(value);
                    } else if (typeof value === 'object' && value !== null) {
                        // 递归搜索对象
                        var searchObj = function(obj, path) {
                            for (var prop in obj) {
                                if (obj.hasOwnProperty(prop)) {
                                    var val = obj[prop];
                                    if (typeof val === 'string' && val.includes('.m3u8') && val.includes('gscdn.kbs.co.kr')) {
                                        configs.push(val);
                                    } else if (typeof val === 'object' && val !== null) {
                                        searchObj(val, path + '.' + prop);
                                    }
                                }
                            }
                        };
                        searchObj(value, key);
                    }
                } catch(e) {}
            }
            return configs;
            """,
            
            # 查找包含认证参数的脚本
            """
            var authUrls = [];
            var scripts = document.getElementsByTagName('script');
            for (var i = 0; i < scripts.length; i++) {
                var content = scripts[i].textContent;
                if (content.includes('Policy=') && content.includes('Signature=')) {
                    // 使用正则表达式提取URL
                    var urlMatch = content.match(/(https?:\/\/[^\s"']*\.m3u8[^\s"']*Policy=[^\s"']*Signature=[^\s"']*)/);
                    if (urlMatch) {
                        authUrls.push(urlMatch[0]);
                    }
                }
            }
            return authUrls;
            """
        ]
        
        for js_script in js_scripts:
            try:
                result = driver.execute_script(js_script)
                if result:
                    if isinstance(result, list):
                        for url in result:
                            if isinstance(url, str) and '.m3u8' in url and 'gscdn.kbs.co.kr' in url:
                                if 'Policy=' in url and 'Signature=' in url:
                                    print(f"✅ 从JS找到认证URL: {url[:100]}...")
                                    return url
                                else:
                                    # 如果没有认证参数，检查是否是基础URL
                                    print(f"🔍 找到基础URL: {url[:100]}...")
                    elif isinstance(result, str) and '.m3u8' in result and 'gscdn.kbs.co.kr' in result:
                        print(f"✅ 从JS找到URL: {result[:100]}...")
                        return result
            except Exception as e:
                continue
        
        # 方法3: 检查视频播放器事件监听器
        print("🎮 检查视频播放器事件...")
        try:
            # 尝试触发视频播放
            trigger_js = """
            // 尝试播放所有视频
            var videos = document.querySelectorAll('video');
            var playedUrls = [];
            for (var i = 0; i < videos.length; i++) {
                try {
                    var video = videos[i];
                    // 设置超时，避免阻塞
                    setTimeout(function(v) {
                        try {
                            v.play();
                        } catch(e) {}
                    }, 100 * i, video);
                } catch(e) {}
            }
            
            // 查找播放按钮并点击
            var playButtons = document.querySelectorAll('button, div, a, span');
            for (var i = 0; i < Math.min(playButtons.length, 20); i++) {
                var btn = playButtons[i];
                var text = (btn.textContent || btn.innerText || '').toLowerCase();
                if (text.includes('play') || text.includes('재생') || text.includes('시작') || 
                    text.includes('시청') || btn.className.includes('play') || btn.id.includes('play')) {
                    try {
                        btn.click();
                    } catch(e) {}
                }
            }
            return 'Triggered play events';
            """
            
            driver.execute_script(trigger_js)
            time.sleep(5)  # 等待可能触发的网络请求
            
        except Exception as e:
            print(f"⚠️ 触发播放事件时出错: {e}")
        
        return None
        
    except Exception as e:
        print(f"❌ 深度分析页面时出错: {e}")
        return None

def wait_for_kbs_advertisement(driver):
    """等待KBS广告结束"""
    print("⏳ 等待KBS广告结束...")
    
    # 总等待时间（包括广告和缓冲）
    total_wait_time = 30  # 15秒广告 + 15秒缓冲
    
    for i in range(total_wait_time):
        time.sleep(1)
        
        # 每5秒检查一次页面状态
        if i % 5 == 0:
            try:
                # 检查是否有"广告"、"AD"等字样
                page_text = driver.page_source.lower()
                if 'ad' in page_text or '광고' in page_text or 'advertisement' in page_text:
                    print(f"  广告中... ({i+1}/{total_wait_time}秒)")
                else:
                    print(f"  页面加载中... ({i+1}/{total_wait_time}秒)")
                    
                # 检查视频元素是否出现
                videos = driver.find_elements(By.TAG_NAME, 'video')
                if videos:
                    print(f"  🎥 发现 {len(videos)} 个视频元素")
                    
            except Exception as e:
                print(f"  检查页面状态时出错: {e}")
    
    print("✅ 广告等待结束")

def get_kbs_m3u8_advanced(driver: webdriver.Chrome, url: str, channel_name: str) -> Optional[str]:
    """
    获取 KBS 的 m3u8 链接（不使用 add_cdp_listener，改用轮询 performance logs）
    1. 访问页面，等待加载
    2. 尝试点击播放按钮
    3. 等待广告
    4. 反复提取 performance logs 中的 m3u8 请求
    5. 若失败，从页面源码提取 Policy/Signature 构造 URL
    6. 最后使用基础 URL 备用
    """
    print(f"🎬 正在获取 {channel_name}...")

    # 清除之前的日志
    driver.get_log('performance')

    # 访问页面
    print(f"🌐 访问 {channel_name} 页面...")
    driver.get(url)
    time.sleep(8)  # 等待初步加载

    # 等待视频元素出现
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )
        print("🎥 视频元素已出现")
    except Exception as e:
        print(f"⚠️ 等待视频元素超时: {e}")

    # ---------- 播放触发 ----------
    play_triggered = False
    # 尝试点击常见播放按钮
    play_selectors = [
        "button[class*='play']", "button[id*='play']",
        "div[class*='play']", "span[class*='play']",
        "a[onclick*='play']", "[aria-label*='play']",
        ".btn-play", ".play-button", ".player-play",
        "button:has-text('재생')", "button:has-text('시청')"
    ]
    for selector in play_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView();", el)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", el)
                    print(f"🖱️ 点击了元素: {selector}")
                    play_triggered = True
                    break
            if play_triggered:
                break
        except:
            continue

    # 如果未找到按钮，直接调用 video.play()
    if not play_triggered:
        try:
            driver.execute_script("""
                var v = document.querySelector('video');
                if(v) v.play();
            """)
            print("🎬 直接执行 video.play()")
            play_triggered = True
        except Exception as e:
            print(f"⚠️ video.play() 失败: {e}")

    # 等待广告（假设广告在播放后开始）
    wait_for_kbs_advertisement(driver)

    # ---------- 轮询 performance logs 捕获 m3u8 请求 ----------
    captured_urls = []
    target_domains = ['gscdn.kbs.co.kr']
    max_wait = 60  # 最长等待60秒
    start_time = time.time()

    while time.time() - start_time < max_wait:
        # 获取新日志
        urls = extract_m3u8_from_network_logs(driver, target_domains)
        for u in urls:
            if u not in captured_urls:
                captured_urls.append(u)
                print(f"📡 捕获到 m3u8 请求: {u[:150]}...")

        # 如果捕获到带认证参数的 URL，直接返回
        for u in captured_urls:
            if 'Policy=' in u and 'Signature=' in u:
                print(f"✅ 找到带认证参数的 URL")
                return u

        # 等待 2 秒后继续
        time.sleep(2)
        print("⏳ 等待 m3u8 请求...")

    # 如果循环结束仍未捕获到认证 URL，但捕获到基础 URL
    if captured_urls:
        print(f"⚠️ 只捕获到基础 URL（无认证参数），尝试使用")
        return captured_urls[0]

    # ---------- 从页面源码提取 Policy/Signature 构造 URL ----------
    print("🔄 尝试从页面源码提取 Policy 和 Signature...")
    page_source = driver.page_source

    # 正则匹配 Policy 和 Signature（注意特殊字符）
    policy_match = re.search(r'Policy=([A-Za-z0-9_\-~]+)', page_source)
    signature_match = re.search(r'Signature=([A-Za-z0-9_\-~]+)', page_source)

    if policy_match and signature_match:
        policy = policy_match.group(1)
        signature = signature_match.group(1)
        base_url = KBS_BASE_URLS.get(channel_name)
        if base_url:
            # 固定 Key-Pair-Id（从你提供的示例中提取）
            key_pair_id = "APKAICDSGT3Y7IXGJ3TA"
            constructed_url = f"{base_url}?Policy={policy}&Key-Pair-Id={key_pair_id}&Signature={signature}"
            print(f"✅ 通过页面参数构造 URL 成功")
            return constructed_url
        else:
            print(f"❌ 找不到 {channel_name} 的基础 URL")

    # ---------- 最后尝试深度分析 ----------
    print("🔄 尝试深度分析页面...")
    deep_url = deep_analyze_kbs_page(driver, channel_name)
    if deep_url:
        return deep_url

    # ---------- 终极备用：基础 URL ----------
    print(f"❌ 所有方法失败，使用基础 URL")
    return KBS_BASE_URLS.get(channel_name)

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
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
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
            
            if channel['name'] == "MBN":
                # MBN特殊处理 - 多画质版本
                mbn_channels = get_mbn_m3u8_multiple_quality(driver)
                dynamic_channels.extend(mbn_channels)
                print(f"✅ {channel['name']} - 获取成功（双画质）")
                continue
            else:
                # KBS频道统一处理
                try:
                    m3u8_url = get_kbs_m3u8_advanced(driver, channel['url'], channel['name'])
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
