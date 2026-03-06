#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新GitHub仓库
全自动方案 - 终极修复版：加入KBS原生API直连 + 强行自动播放解除限制
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
from webdriver_manager.chrome import ChromeDriverManager

# 配置信息
GITHUB_USERNAME = "GoonhoLee"
STABLE_REPO_NAME = "koreaiptv-auto-updater" # 修正了你的仓库名
FULL_ACCESS_TOKEN = os.getenv('FULL_ACCESS_TOKEN')

# 电视台配置
CHANNELS = [
    {"name": "KBS1", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=11&ch_type=globalList", "tvg_id": "KBS1.kr"},
    {"name": "KBS2", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=12&ch_type=globalList", "tvg_id": "KBS2.kr"},
    {"name": "KBS 24", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=81&ch_type=globalList", "tvg_id": "KBS24.kr"},
    {"name": "MBN", "url": "https://www.mbn.co.kr/vod/onair", "tvg_id": "MBN.kr"},
    {"name": "KBS DRAMA", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N91&ch_type=globalList", "tvg_id": "KBSDRAMA.kr"},
    {"name": "KBS JOY", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N92&ch_type=globalList", "tvg_id": "KBSJOY.kr"},
    {"name": "KBS STORY", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N94&ch_type=globalList", "tvg_id": "KBSSTORY.kr"},
    {"name": "KBS LIFE", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N93&ch_type=globalList", "tvg_id": "KBSLIFE.kr"}
]

# 静态频道列表
STATIC_CHANNELS = [
    '#EXTINF:-1 tvg-id="TVChosun.kr",TV Chosun (720p)',
    '#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on.cstv',
    'https://onaircdn.tvchosun.com/origin1/_definst_/tvchosun_s3/chunklist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="TVChosun2.kr",TV Chosun 2 (720p)',
    '#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on2.cstv',
    'https://onair2cdn.tvchosun.com/origin2/_definst_/tvchosun_s3/chunklist.m3u8',
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
    
    # 🌟 核心修复1：允许无头浏览器自动播放视频（解决 KBS 播放器卡主不请求的问题）
    chrome_options.add_argument('--autoplay-policy=no-user-gesture-required')
    chrome_options.add_argument('--mute-audio')
    
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
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

def get_kbs_m3u8_advanced(driver: webdriver.Chrome, url: str, channel_name: str) -> Optional[str]:
    """修复版：API直连拦截 + 自动播放修复"""
    print(f"🎬 正在获取 {channel_name}...")
    
    # 🌟 核心修复2：直接抓取 KBS 底层 API (无视浏览器环境，速度极快)
    try:
        ch_code_match = re.search(r'ch_code=([^&]+)', url)
        if ch_code_match:
            ch_code = ch_code_match.group(1)
            api_url = f"https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/{ch_code}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Origin": "https://onair.kbs.co.kr",
                "Referer": "https://onair.kbs.co.kr/"
            }
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                channel_items = data.get("channel_item", [])
                if channel_items:
                    service_url = channel_items[0].get("service_url")
                    if service_url and ".m3u8" in service_url and "Policy=" in service_url:
                        print(f"✅ [API提取] 成功秒取真实地址: {service_url[:80]}...")
                        return service_url
    except Exception as e:
        print(f"⚠️ API直连失败，正在切换至浏览器模拟模式: {e}")

    # 如果 API 失败，退回使用浏览器抓包 (此时自动播放已解除限制)
    try:
        driver.get_log('performance') 
        driver.get(url)
        print("⏳ 页面已加载，监控真实地址生成 (最多等待15秒)...")
        
        start_time = time.time()
        while time.time() - start_time < 15:
            found_url = driver.execute_script("""
                var logs = window.performance.getEntriesByType('resource');
                for (var i=0; i < logs.length; i++) {
                    if (logs[i].name.includes('.m3u8') && logs[i].name.includes('Policy=')) {
                        return logs[i].name;
                    }
                }
                return null;
            """)
            
            if found_url:
                print(f"✅ [浏览器提取] 成功截获带认证参数的URL: {found_url[:80]}...")
                return found_url
            time.sleep(2) 
            
        print(f"❌ 未能获取到带认证的M3U8，退回到基础URL...")
        return KBS_BASE_URLS.get(channel_name)
    except Exception as e:
        print(f"❌ 获取 {channel_name} 时出错: {str(e)}")
        return KBS_BASE_URLS.get(channel_name)

# ========== MBN 处理逻辑 ==========

def get_real_mbn_url_from_response(auth_url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.mbn.co.kr/vod/onair'
        }
        response = requests.get(auth_url, headers=headers, timeout=(5, 10))
        if response.status_code == 200:
            content = response.text.strip()
            if content.startswith('http') and '.m3u8' in content and 'hls-live.mbn.co.kr' in content:
                return content
    except: pass
    return None

def get_mbn_m3u8_multiple_quality(driver):
    mbn_channels = []
    try:
        print("🚀 正在获取 MBN 多画质版本...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        time.sleep(15)
        
        m3u8_urls = extract_m3u8_from_network_logs(driver, ['mbn.co.kr', 'hls-live.mbn.co.kr'])
        auth_urls = [url for url in m3u8_urls if 'mbnStreamAuth' in url]
        
        quality_configs = [
            {'quality': '1000k', 'name': 'MBN（高画质）', 'tvg_id': 'MBN.kr', 'auth_urls': [url for url in auth_urls if '1000k' in url], 'base_url': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8'},
            {'quality': '600k', 'name': 'MBN（标清）', 'tvg_id': 'MBN.kr', 'auth_urls': [url for url in auth_urls if '600k' in url], 'base_url': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8'}
        ]
        
        for config in quality_configs:
            print(f"🎯 正在获取 {config['quality']} 版本...")
            real_url = None
            if config['auth_urls']:
                real_url = get_real_mbn_url_from_response(config['auth_urls'][0])
            if not real_url:
                constructed_auth_url = f"https://www.mbn.co.kr/player/mbnStreamAuth_new_live.mbn?vod_url={config['base_url']}"
                real_url = get_real_mbn_url_from_response(constructed_auth_url)
            
            if real_url:
                mbn_channels.append({'name': config['name'], 'tvg_id': config['tvg_id'], 'url': real_url, 'quality': config['quality']})
        return mbn_channels
    except Exception as e:
        print(f"❌ 获取 MBN 出错: {e}")
        return []

# ========== GitHub 更新和列表生成 ==========

def update_stable_repository(content):
    if not FULL_ACCESS_TOKEN:
        print("❌ 未找到FULL_ACCESS_TOKEN，跳过GitHub仓库更新")
        return False
        
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/contents/korean_tv.m3u"
    headers = {"Authorization": f"token {FULL_ACCESS_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    try:
        response = requests.get(url, headers=headers)
        sha = response.json().get('sha') if response.status_code == 200 else None
        
        data = {
            "message": f"自动更新播放列表 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": base64.b64encode(content.encode('utf-8')).decode('ascii'),
            "committer": {"name": "GitHub Action", "email": "action@github.com"}
        }
        if sha: data["sha"] = sha
            
        response = requests.put(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            print("🎉 GitHub仓库更新成功!")
            return True
    except Exception as e:
        print(f"❌ 更新GitHub出错: {e}")
    return False

def generate_playlist(dynamic_channels):
    lines = ["#EXTM3U", f"# 自动生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    later_channels = ['KBS DRAMA', 'KBS JOY', 'KBS STORY', 'KBS LIFE']
    
    for channel in dynamic_channels:
        if channel.get('url') and channel['name'] not in later_channels:
            lines.extend([f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}",{channel["name"]}', channel['url'], ""])
            
    lines.extend(STATIC_CHANNELS)
    lines.append("")
    
    for channel in dynamic_channels:
        if channel.get('url') and channel['name'] in later_channels:
            lines.extend([f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}",{channel["name"]}', channel['url'], ""])
            
    return "\n".join(lines)

def main():
    start_time = time.time()
    print("🎬 开始获取M3U8链接...")
    
    driver = None
    try:
        driver = setup_driver()
        dynamic_channels = []
        
        for channel in CHANNELS:
            print(f"\n{'='*50}\n🔍 正在处理频道: {channel['name']}")
            if channel['name'] == "MBN": 
                mbn_channels = get_mbn_m3u8_multiple_quality(driver)
                dynamic_channels.extend(mbn_channels)
                if mbn_channels: print(f"✅ {channel['name']} - 获取成功（双画质）")
            else:
                m3u8_url = get_kbs_m3u8_advanced(driver, channel['url'], channel['name'])
                if m3u8_url:
                    dynamic_channels.append({'name': channel['name'], 'tvg_id': channel['tvg_id'], 'url': m3u8_url})
                    print(f"✅ {channel['name']} - 获取成功")
                    
        print(f"\n{'='*50}\n✅ 播放列表生成完成!")
        standard_playlist = generate_playlist(dynamic_channels)
        update_stable_repository(standard_playlist)

        with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
            f.write(standard_playlist)
        print("💾 播放列表已保存到本地: korean_tv.m3u")
        
    finally:
        if driver: driver.quit()
        print(f"⏱️ 总执行时间: {time.time() - start_time:.2f}秒")

if __name__ == "__main__":
    main()
