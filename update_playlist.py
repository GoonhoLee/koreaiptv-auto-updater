#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新GitHub仓库
KBS频道抓取改进版本 - 直接提取JavaScript中的认证逻辑
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

def extract_m3u8_from_network_logs(driver, target_domains):
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
                        if url and '.m3u8' in url and any(domain in url for domain in target_domains):
                            m3u8_urls.append(url)
                            
            except Exception:
                continue
                
    except Exception as e:
        print(f"⚠️ 读取网络日志时出错: {e}")
    
    return list(set(m3u8_urls))

def extract_kbs_params_from_js(driver, channel_name):
    """从JavaScript中提取KBS认证参数"""
    try:
        print("🔍 分析JavaScript代码寻找认证逻辑...")
        
        # 获取所有JavaScript代码
        scripts = driver.find_elements(By.TAG_NAME, 'script')
        all_js_code = ""
        
        for script in scripts:
            try:
                js_code = driver.execute_script("return arguments[0].textContent", script)
                all_js_code += js_code + "\n"
            except:
                continue
        
        # 查找可能的认证参数
        patterns = [
            # 查找Policy参数
            r'Policy=([A-Za-z0-9_\-~]+)',
            r'["\']Policy["\'][:\s]*["\']([A-Za-z0-9_\-~]+)["\']',
            r'policy["\']?\s*:\s*["\']([A-Za-z0-9_\-~]+)["\']',
            # 查找Signature参数
            r'Signature=([A-Za-z0-9_\-~]+)',
            r'["\']Signature["\'][:\s]*["\']([A-Za-z0-9_\-~]+)["\']',
            r'signature["\']?\s*:\s*["\']([A-Za-z0-9_\-~]+)["\']',
            # 查找完整的m3u8 URL
            r'(https?://[^\s"\']*\.m3u8\?[^\s"\']*Policy=[^\s"\']*Signature=[^\s"\']*)',
            r'["\'](https?://[^"\']*\.m3u8\?[^"\']*Policy=[^"\']*Signature=[^"\']*)["\']',
        ]
        
        found_params = []
        
        for pattern in patterns:
            matches = re.findall(pattern, all_js_code, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                # 检查是否包含必要的参数
                if 'Policy=' in match and 'Signature=' in match and 'gscdn.kbs.co.kr' in match:
                    found_params.append(match)
                    print(f"✅ 从JS找到认证URL: {match[:100]}...")
                elif 'Policy=' in match or 'Signature=' in match:
                    # 只找到部分参数
                    print(f"🔍 找到部分参数: {match[:50]}...")
        
        # 如果有找到完整URL，返回第一个
        if found_params:
            return found_params[0]
        
        # 如果没有找到完整URL，尝试查找分开的参数
        policy = None
        signature = None
        
        policy_patterns = [
            r'Policy=([A-Za-z0-9_\-~]+)',
            r'"Policy":"([A-Za-z0-9_\-~]+)"',
            r"'Policy':'([A-Za-z0-9_\-~]+)'",
        ]
        
        signature_patterns = [
            r'Signature=([A-Za-z0-9_\-~]+)',
            r'"Signature":"([A-Za-z0-9_\-~]+)"',
            r"'Signature':'([A-Za-z0-9_\-~]+)'",
        ]
        
        for pattern in policy_patterns:
            matches = re.findall(pattern, all_js_code)
            if matches:
                policy = matches[0]
                break
        
        for pattern in signature_patterns:
            matches = re.findall(pattern, all_js_code)
            if matches:
                signature = matches[0]
                break
        
        if policy and signature:
            print(f"✅ 找到分开的参数: Policy和Signature")
            return f"Policy={policy}&Signature={signature}"
        
        return None
        
    except Exception as e:
        print(f"⚠️ 分析JavaScript时出错: {e}")
        return None

def execute_kbs_player_js(driver):
    """执行KBS播放器的JavaScript来获取流媒体地址"""
    try:
        print("💻 尝试执行播放器JavaScript...")
        
        # 尝试多种方法来触发播放器并获取地址
        scripts = [
            # 方法1: 尝试调用播放器API
            """
            try {
                if (window.player && window.player.getSrc) {
                    return window.player.getSrc();
                }
                if (window.videojs && window.videojs.getPlayers()) {
                    var players = window.videojs.getPlayers();
                    for (var playerId in players) {
                        if (players[playerId].src) {
                            return players[playerId].src();
                        }
                    }
                }
                return '';
            } catch(e) {
                return '';
            }
            """,
            
            # 方法2: 查找所有视频源
            """
            var sources = [];
            var videos = document.querySelectorAll('video');
            videos.forEach(function(video) {
                if (video.src) sources.push(video.src);
                if (video.currentSrc) sources.push(video.currentSrc);
            });
            
            var sources2 = document.querySelectorAll('source[src*=".m3u8"]');
            sources2.forEach(function(source) {
                sources.push(source.src);
            });
            
            return sources.length > 0 ? sources[0] : '';
            """,
            
            # 方法3: 尝试触发播放并获取网络请求
            """
            try {
                // 创建观察者来监控网络请求
                var originalFetch = window.fetch;
                var m3u8Url = '';
                
                window.fetch = function() {
                    var url = arguments[0];
                    if (url && url.includes('.m3u8') && url.includes('kbs')) {
                        m3u8Url = url;
                    }
                    return originalFetch.apply(this, arguments);
                };
                
                // 尝试播放视频
                var videos = document.querySelectorAll('video');
                if (videos.length > 0) {
                    videos[0].play().catch(function(e) {
                        console.log('Play failed:', e);
                    });
                }
                
                // 等待一下
                setTimeout(function() {
                    return m3u8Url;
                }, 1000);
                
                return m3u8Url;
            } catch(e) {
                return '';
            }
            """
        ]
        
        for script in scripts:
            try:
                result = driver.execute_script(script)
                if result and '.m3u8' in result and 'gscdn.kbs.co.kr' in result:
                    print(f"✅ 从播放器JS获取到地址: {result[:100]}...")
                    return result
            except Exception as e:
                continue
        
        return None
        
    except Exception as e:
        print(f"⚠️ 执行播放器JS时出错: {e}")
        return None

def get_kbs_m3u8(driver: webdriver.Chrome, url: str, channel_name: str) -> Optional[str]:
    """获取KBS的m3u8链接 - 综合方法"""
    try:
        print(f"🎬 正在获取 {channel_name}...")
        
        # 清除之前的网络日志
        driver.get_log('performance')
        
        # 访问页面
        driver.get(url)
        
        # 等待页面加载（包括广告）
        print(f"⏳ 等待 {channel_name} 页面完全加载（25秒）...")
        time.sleep(25)
        
        # 方法1: 尝试从JavaScript中直接提取认证参数
        print("🔍 方法1: 提取JavaScript中的认证参数...")
        auth_url = extract_kbs_params_from_js(driver, channel_name)
        
        if auth_url:
            if auth_url.startswith('http'):
                print(f"✅ 方法1成功: 找到完整认证URL")
                return auth_url
            elif 'Policy=' in auth_url and 'Signature=' in auth_url:
                # 只有参数，需要构建完整URL
                if channel_name in KBS_BASE_URLS:
                    base_url = KBS_BASE_URLS[channel_name]
                    full_url = f"{base_url}?{auth_url}&Key-Pair-Id=APKAICDSGT3Y7IXGJ3TA"
                    print(f"✅ 方法1成功: 构建完整认证URL")
                    return full_url
        
        # 方法2: 尝试执行播放器JavaScript
        print("🔍 方法2: 执行播放器JavaScript...")
        player_url = execute_kbs_player_js(driver)
        
        if player_url and '.m3u8' in player_url and 'gscdn.kbs.co.kr' in player_url:
            print(f"✅ 方法2成功: 从播放器获取地址")
            return player_url
        
        # 方法3: 监控网络请求
        print("🔍 方法3: 监控网络请求...")
        m3u8_urls = extract_m3u8_from_network_logs(driver, ['gscdn.kbs.co.kr'])
        
        # 过滤出认证URL
        auth_urls = [url for url in m3u8_urls if 'Policy=' in url and 'Signature=' in url]
        
        if auth_urls:
            print(f"✅ 方法3成功: 找到 {len(auth_urls)} 个认证URL")
            # 优先选择与频道名匹配的URL
            for url in auth_urls:
                if channel_name.lower().replace(' ', '') in url.lower():
                    print(f"🔗 选择匹配URL: {url[:100]}...")
                    return url
            print(f"🔗 选择第一个URL: {auth_urls[0][:100]}...")
            return auth_urls[0]
        
        # 方法4: 尝试点击播放按钮并重新监控
        print("🔍 方法4: 尝试交互操作...")
        try:
            # 查找并点击播放按钮
            play_buttons = driver.find_elements(By.XPATH, 
                "//button[contains(text(), '재생') or contains(text(), '시청') or contains(text(), 'PLAY') or contains(text(), 'play')] | " +
                "//a[contains(text(), '재생') or contains(text(), '시청') or contains(text(), 'PLAY') or contains(text(), 'play')] | " +
                "//div[contains(text(), '재생') or contains(text(), '시청') or contains(text(), 'PLAY') or contains(text(), 'play')]")
            
            for button in play_buttons[:3]:  # 尝试前3个按钮
                try:
                    print(f"🖱️ 尝试点击播放按钮: {button.text[:20] if button.text else '无文本'}")
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(5)
                    
                    # 点击后重新监控网络
                    new_urls = extract_m3u8_from_network_logs(driver, ['gscdn.kbs.co.kr'])
                    new_auth_urls = [url for url in new_urls if 'Policy=' in url and 'Signature=' in url]
                    
                    if new_auth_urls:
                        print(f"✅ 点击后找到认证URL: {new_auth_urls[0][:100]}...")
                        return new_auth_urls[0]
                except:
                    continue
        except Exception as e:
            print(f"⚠️ 点击播放按钮时出错: {e}")
        
        # 方法5: 刷新页面重试
        print("🔍 方法5: 刷新页面重试...")
        driver.refresh()
        time.sleep(15)
        
        # 重新尝试所有方法
        auth_url = extract_kbs_params_from_js(driver, channel_name)
        if auth_url and auth_url.startswith('http'):
            return auth_url
        
        # 最终备用方案
        print(f"❌ 所有方法都失败，使用基础URL: {channel_name}")
        if channel_name in KBS_BASE_URLS:
            return KBS_BASE_URLS[channel_name]
        
        return None
        
    except Exception as e:
        print(f"❌ 获取 {channel_name} 时出错: {str(e)}")
        import traceback
        traceback.print_exc()
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
            
            if channel['name'] == "MBN":  # 精确匹配MBN
                # MBN特殊处理 - 多画质版本
                mbn_channels = get_mbn_m3u8_multiple_quality(driver)
                dynamic_channels.extend(mbn_channels)
                print(f"✅ {channel['name']} - 获取成功（双画质）")
                continue  # 跳过MBN的常规处理
            else:
                # KBS频道统一处理
                try:
                    m3u8_url = get_kbs_m3u8(driver, channel['url'], channel['name'])
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
