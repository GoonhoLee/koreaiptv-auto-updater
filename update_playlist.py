#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新GitHub仓库
修复KBS抓取问题：弃用UI模拟，改用 KBS 官方 API 接口直连
"""

import requests
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
# 注意：KBS 这里我们只需要 code，不需要原始播放页 URL
CHANNELS = [
    # KBS 频道 (使用 API Code)
    {"name": "KBS1",      "code": "11",  "tvg_id": "KBS1.kr", "type": "KBS"},
    {"name": "KBS2",      "code": "12",  "tvg_id": "KBS2.kr", "type": "KBS"},
    {"name": "KBS 24",    "code": "81",  "tvg_id": "KBS24.kr", "type": "KBS"},
    {"name": "KBS DRAMA", "code": "N91", "tvg_id": "KBSDRAMA.kr", "type": "KBS"},
    {"name": "KBS JOY",   "code": "N92", "tvg_id": "KBSJOY.kr", "type": "KBS"},
    {"name": "KBS STORY", "code": "N94", "tvg_id": "KBSSTORY.kr", "type": "KBS"},
    {"name": "KBS LIFE",  "code": "N93", "tvg_id": "KBSLIFE.kr", "type": "KBS"},
    
    # MBN 频道 (保留原有逻辑)
    {"name": "MBN",       "url": "https://www.mbn.co.kr/vod/onair", "tvg_id": "MBN.kr", "type": "MBN"},
]

# 静态频道列表
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

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 模拟真实 PC 浏览器，这对 API 访问很重要
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    # 开启日志 (MBN需要)
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

def get_kbs_via_api(driver: webdriver.Chrome, code: str, channel_name: str) -> Optional[str]:
    """通过 KBS 官方 API 直接获取 m3u8 (绕过播放器UI)"""
    try:
        print(f"🎬 正在通过 API 获取 {channel_name} (Code: {code})...")
        
        # KBS 内部 API 地址，直接返回包含 m3u8 的 JSON
        api_url = f"https://kapi.kbs.co.kr/api/v1/landing/live/channel_code/{code}"
        
        # 使用 Selenium 访问 API (为了带上浏览器的 Cookie/Headers)
        driver.get(api_url)
        
        # 提取页面内容 (JSON)
        page_source = driver.find_element(By.TAG_NAME, 'body').text
        
        try:
            data = json.loads(page_source)
            # 解析 JSON 结构: channel_item -> streams -> service_url
            if "channel_item" in data and len(data["channel_item"]) > 0:
                streams = data["channel_item"][0].get("streams", [])
                if streams:
                    # 优先找 hls 类型
                    for stream in streams:
                        if stream.get("service_url"):
                            m3u8_url = stream["service_url"]
                            print(f"✅ API 成功返回地址")
                            # 简单的验证
                            if "Policy=" in m3u8_url:
                                return m3u8_url
                            else:
                                print(f"⚠️ 获取到的地址似乎没有签名，可能已失效，但仍尝试返回")
                                return m3u8_url
            
            print(f"❌ API 返回了 JSON，但未找到 streams 字段。可能是地区限制。")
            # 如果是在 GitHub Actions (US IP)，这里大概率会失败
            if "geoblock" in page_source.lower():
                print("🚫 检测到地区封锁 (Geo-blocked)")
                
        except json.JSONDecodeError:
            print(f"❌ API 返回的不是有效 JSON: {page_source[:100]}...")
            
        return None

    except Exception as e:
        print(f"❌ API 请求出错: {str(e)}")
        return None

def extract_m3u8_from_network_logs(driver, target_domains):
    """(保留给MBN使用) 从网络日志中提取m3u8链接"""
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
                            if not target_domains or any(domain in url for domain in target_domains):
                                m3u8_urls.append(url)
            except Exception:
                continue
    except Exception:
        pass
    return list(set(m3u8_urls))

def get_real_mbn_url_from_response(auth_url):
    """MBN 辅助函数"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.mbn.co.kr/vod/onair'
        }
        response = requests.get(auth_url, headers=headers, timeout=10)
        if response.status_code == 200 and '.m3u8' in response.text:
            return response.text.strip()
    except:
        pass
    return None

def get_mbn_m3u8_multiple_quality(driver):
    """MBN 抓取逻辑 (保持不变)"""
    mbn_channels = []
    try:
        print("🚀 获取 MBN...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        time.sleep(10)
        
        m3u8_urls = extract_m3u8_from_network_logs(driver, ['mbn.co.kr'])
        auth_urls = [url for url in m3u8_urls if 'mbnStreamAuth' in url]
        
        configs = [
            {'q': '1000k', 'name': 'MBN（高画质）', 'base': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8'},
            {'q': '600k',  'name': 'MBN（标清）',   'base': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8'}
        ]
        
        for cfg in configs:
            real_url = None
            valid_auths = [u for u in auth_urls if cfg['q'] in u]
            if valid_auths:
                real_url = get_real_mbn_url_from_response(valid_auths[0])
            
            if not real_url:
                auth_url = f"https://www.mbn.co.kr/player/mbnStreamAuth_new_live.mbn?vod_url={cfg['base']}"
                real_url = get_real_mbn_url_from_response(auth_url)
                
            if real_url:
                mbn_channels.append({'name': cfg['name'], 'tvg_id': 'MBN.kr', 'url': real_url})
                print(f"  ✅ {cfg['name']}")
                
        return mbn_channels
    except Exception as e:
        print(f"❌ MBN出错: {e}")
        return []

def update_stable_repository(content):
    if not FULL_ACCESS_TOKEN:
        print("❌ 无Token，跳过 GitHub 更新")
        return False
    
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/contents/korean_tv.m3u"
    headers = {"Authorization": f"token {FULL_ACCESS_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    try:
        resp = requests.get(url, headers=headers)
        sha = resp.json().get('sha') if resp.status_code == 200 else None
        
        data = {
            "message": f"Update {datetime.now().strftime('%Y-%m-%d')}",
            "content": base64.b64encode(content.encode('utf-8')).decode('ascii'),
            "committer": {"name": "GitHub Action", "email": "action@github.com"}
        }
        if sha: data["sha"] = sha
        
        requests.put(url, headers=headers, json=data)
        print("🎉 GitHub仓库更新成功!")
        return True
    except Exception as e:
        print(f"❌ GitHub更新失败: {e}")
        return False

def generate_playlist(dynamic_channels):
    lines = ["#EXTM3U", f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    later_channels = ['KBS DRAMA', 'KBS JOY', 'KBS STORY', 'KBS LIFE']
    
    # 普通频道
    for ch in dynamic_channels:
        if ch['name'] not in later_channels:
            lines.append(f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}",{ch["name"]}')
            lines.append(ch['url'])
            lines.append("")
            
    # 静态频道
    lines.extend(STATIC_CHANNELS)
    lines.append("")
    
    # KBS 有线频道
    for ch in dynamic_channels:
        if ch['name'] in later_channels:
            lines.append(f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}",{ch["name"]}')
            lines.append(ch['url'])
            lines.append("")
            
    return "\n".join(lines)

def main():
    print("🎬 开始运行 (KBS API 模式)...")
    driver = setup_driver()
    channels_data = []
    
    try:
        for channel in CHANNELS:
            # MBN 逻辑
            if channel["type"] == "MBN":
                channels_data.extend(get_mbn_m3u8_multiple_quality(driver))
            
            # KBS 逻辑 (API)
            elif channel["type"] == "KBS":
                url = get_kbs_via_api(driver, channel['code'], channel['name'])
                if url:
                    channels_data.append({
                        'name': channel['name'],
                        'tvg_id': channel['tvg_id'],
                        'url': url
                    })
        
        playlist = generate_playlist(channels_data)
        
        # 保存本地
        with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
            f.write(playlist)
            
        # 更新GitHub
        update_stable_repository(playlist)
        
        print(f"📊 完成！成功获取 {len(channels_data)} 个频道")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
