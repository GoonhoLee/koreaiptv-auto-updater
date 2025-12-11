#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新GitHub仓库
修复KBS抓取逻辑：改用官方API接口直连，无需等待广告
保留MBN多画质支持
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
# 注意：为 KBS 添加了 'code' 字段，这是 API 必须的
CHANNELS = [
    # --- KBS 系列 (使用 API) ---
    {
        "name": "KBS1",
        "code": "11",
        "url": "https://onair.kbs.co.kr/...", # 仅作参考，实际使用API
        "tvg_id": "KBS1.kr",
        "type": "KBS"
    },
    {
        "name": "KBS2", 
        "code": "12",
        "url": "https://onair.kbs.co.kr/...",
        "tvg_id": "KBS2.kr",
        "type": "KBS"
    },
    {
        "name": "KBS 24",
        "code": "81",
        "url": "https://onair.kbs.co.kr/...",
        "tvg_id": "KBS24.kr",
        "type": "KBS"
    },
    {
        "name": "KBS DRAMA",
        "code": "N91",
        "url": "https://onair.kbs.co.kr/...",
        "tvg_id": "KBSDRAMA.kr",
        "type": "KBS"
    },
    {
        "name": "KBS JOY",
        "code": "N92",
        "url": "https://onair.kbs.co.kr/...",
        "tvg_id": "KBSJOY.kr",
        "type": "KBS"
    },
    {
        "name": "KBS STORY",
        "code": "N94",
        "url": "https://onair.kbs.co.kr/...",
        "tvg_id": "KBSSTORY.kr",
        "type": "KBS"
    },
    {
        "name": "KBS LIFE",
        "code": "N93",
        "url": "https://onair.kbs.co.kr/...",
        "tvg_id": "KBSLIFE.kr",
        "type": "KBS"
    },
    # --- MBN (使用原有网页抓取) ---
    {
        "name": "MBN",
        "url": "https://www.mbn.co.kr/vod/onair",
        "tvg_id": "MBN.kr",
        "type": "MBN"
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

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new') # 使用新版 Headless 模式，兼容性更好
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 开启性能日志（仅MBN需要）
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_kbs_m3u8_api(driver: webdriver.Chrome, code: str, channel_name: str) -> Optional[str]:
    """
    通过KBS官方API获取直播地址
    优点：无需等待广告，速度快，直接返回带签名的m3u8
    """
    try:
        print(f"🎬 [API] 正在请求 {channel_name} (Code: {code})...")
        
        # KBS 官方 API 地址
        api_url = f"https://kapi.kbs.co.kr/api/v1/landing/live/channel_code/{code}"
        
        # 使用 Selenium 访问 API 以便处理 Headers/Cookies 问题
        driver.get(api_url)
        
        # 提取页面文本（即JSON响应）
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        try:
            data = json.loads(page_text)
            
            # 解析 JSON 结构
            # channel_item -> streams -> service_url
            if "channel_item" in data and len(data["channel_item"]) > 0:
                streams = data["channel_item"][0].get("streams", [])
                if streams:
                    # 通常取第一个流，或者查找 hls 类型
                    for stream in streams:
                        url = stream.get("service_url")
                        if url and ".m3u8" in url:
                            print(f"✅ {channel_name} API 获取成功")
                            return url
                            
            print(f"❌ {channel_name} API 返回数据异常或无流信息")
            # 如果你在海外，可能会遇到 Geo-block
            if "geoblock" in page_text.lower():
                print("⚠️ 检测到地区限制 (Geo-blocked)")
                
            return None
            
        except json.JSONDecodeError:
            print(f"❌ {channel_name} API 返回非 JSON 格式")
            return None
            
    except Exception as e:
        print(f"❌ 获取 {channel_name} API 时出错: {str(e)}")
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
                        if url and '.m3u8' in url and any(domain in url for domain in target_domains):
                            m3u8_urls.append(url)
                            
            except Exception:
                continue
                
    except Exception as e:
        print(f"⚠️ 读取网络日志时出错: {e}")
    
    return list(set(m3u8_urls))

def get_real_mbn_url_from_response(auth_url):
    """(保留给MBN使用)"""
    try:
        print(f"🔗 请求MBN认证链接: {auth_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.mbn.co.kr/vod/onair'
        }
        response = requests.get(auth_url, headers=headers, timeout=(5, 10))
        if response.status_code == 200:
            content = response.text.strip()
            if content.startswith('http') and '.m3u8' in content:
                print(f"✅ 获取到MBN地址: {content}")
                return content
    except Exception as e:
        print(f"❌ MBN认证出错: {str(e)}")
    return None

def get_mbn_m3u8_multiple_quality(driver):
    """(保留给MBN使用) 获取MBN的m3u8链接"""
    mbn_channels = []
    try:
        print("🚀 正在获取 MBN 多画质版本...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        time.sleep(15) # MBN 仍需等待加载
        
        m3u8_urls = []
        target_domains = ['mbn.co.kr', 'hls-live.mbn.co.kr']
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        auth_urls = [url for url in m3u8_urls if 'mbnStreamAuth' in url]
        
        quality_configs = [
            {'quality': '1000k', 'name': 'MBN（高画质）', 'base_url': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8'},
            {'quality': '600k', 'name': 'MBN（标清）', 'base_url': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8'}
        ]
        
        for config in quality_configs:
            real_url = None
            # 尝试自动发现
            relevant_auths = [url for url in auth_urls if config['quality'] in url]
            if relevant_auths:
                real_url = get_real_mbn_url_from_response(relevant_auths[0])
            
            # 尝试构造
            if not real_url:
                constructed = f"https://www.mbn.co.kr/player/mbnStreamAuth_new_live.mbn?vod_url={config['base_url']}"
                real_url = get_real_mbn_url_from_response(constructed)
            
            if real_url:
                mbn_channels.append({
                    'name': config['name'],
                    'tvg_id': 'MBN.kr',
                    'url': real_url,
                    'quality': config['quality']
                })
                
        return mbn_channels
    except Exception as e:
        print(f"❌ MBN 获取出错: {e}")
        return []

def update_stable_repository(content):
    """更新GitHub仓库"""
    if not FULL_ACCESS_TOKEN:
        print("❌ 未找到FULL_ACCESS_TOKEN，跳过更新")
        return False
        
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/contents/korean_tv.m3u"
    headers = {"Authorization": f"token {FULL_ACCESS_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    try:
        response = requests.get(url, headers=headers)
        sha = response.json().get('sha') if response.status_code == 200 else None
        
        data = {
            "message": f"Auto-update {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": base64.b64encode(content.encode('utf-8')).decode('ascii'),
            "committer": {"name": "GitHub Action", "email": "action@github.com"}
        }
        if sha: data["sha"] = sha
        
        requests.put(url, headers=headers, json=data)
        print("🎉 GitHub仓库更新成功!")
        return True
    except Exception as e:
        print(f"❌ GitHub更新出错: {e}")
        return False

def generate_playlist(dynamic_channels):
    """生成M3U"""
    lines = ["#EXTM3U", f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    later_channels = ['KBS DRAMA', 'KBS JOY', 'KBS STORY', 'KBS LIFE']
    
    # 动态频道
    for channel in dynamic_channels:
        if channel.get('url') and channel['name'] not in later_channels:
            lines.append(f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}",{channel["name"]}')
            lines.append(channel['url'])
            lines.append("")
    
    # 静态频道
    lines.extend(STATIC_CHANNELS)
    lines.append("")
    
    # 底部KBS频道
    for channel in dynamic_channels:
        if channel.get('url') and channel['name'] in later_channels:
            lines.append(f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}",{channel["name"]}')
            lines.append(channel['url'])
            lines.append("")
            
    return "\n".join(lines)

def main():
    """主函数"""
    start_time = time.time()
    print("🎬 开始任务...")
    
    driver = None
    try:
        driver = setup_driver()
        dynamic_channels = []
        
        for channel in CHANNELS:
            print(f"🔍 处理频道: {channel['name']}")
            
            # --- 策略分流 ---
            if channel.get("type") == "MBN":
                # MBN 使用原有的日志抓取方式
                mbn_res = get_mbn_m3u8_multiple_quality(driver)
                dynamic_channels.extend(mbn_res)
                
            elif channel.get("type") == "KBS":
                # KBS 使用新的 API 方式
                url = get_kbs_m3u8_api(driver, channel['code'], channel['name'])
                if url:
                    dynamic_channels.append({
                        'name': channel['name'],
                        'tvg_id': channel['tvg_id'],
                        'url': url
                    })
        
        # 生成和保存
        playlist = generate_playlist(dynamic_channels)
        with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
            f.write(playlist)
            
        update_stable_repository(playlist)
        
        print(f"📊 成功获取 {len(dynamic_channels)} 个动态源")
        
    finally:
        if driver:
            driver.quit()
        print(f"⏱️ 耗时: {time.time() - start_time:.2f}秒")

if __name__ == "__main__":
    main()
