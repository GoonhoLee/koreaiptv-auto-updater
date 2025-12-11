#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新GitHub仓库
修复KBS抓取问题：解决 move target out of bounds 错误，改用 JS 注入控制播放
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    chrome_options.add_argument('--headless=new') # 使用新版headless模式
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--start-maximized') # 尝试最大化
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 自动播放策略
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    chrome_options.add_argument("--mute-audio")
    
    # 模拟真实浏览器
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    # 开启日志
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 反检测
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
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
                        if url and '.m3u8' in url:
                            if not target_domains or any(domain in url for domain in target_domains):
                                m3u8_urls.append(url)
            except Exception:
                continue
    except Exception as e:
        print(f"⚠️ 读取日志错: {e}")
    return list(set(m3u8_urls))

def get_kbs_m3u8(driver: webdriver.Chrome, url: str, channel_name: str) -> Optional[str]:
    """获取KBS的m3u8链接 - 纯JS操作版"""
    try:
        print(f"🎬 正在获取 {channel_name}...")
        
        kbs_signatures = {
            "KBS1": "1tv.gscdn",
            "KBS2": "2tv.gscdn",
            "KBS 24": "news24.gscdn",
            "KBS DRAMA": "kbsndrama.gscdn",
            "KBS JOY": "kbsnjoy.gscdn",
            "KBS STORY": "kbsnw.gscdn",
            "KBS LIFE": "kbsnlife.gscdn"
        }
        target_signature = kbs_signatures.get(channel_name, "gscdn.kbs")
        
        driver.get(url)
        
        # 1. 等待视频标签出现 (最多10秒)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
        except:
            print("  ⚠️ 未找到video标签，页面可能加载缓慢")

        # 2. 使用JavaScript强制触发播放 (不依赖鼠标坐标)
        print("💻 执行JS强制播放...")
        driver.execute_script("""
            // 策略1: 找到所有video标签强制播放
            var vids = document.querySelectorAll('video');
            vids.forEach(v => { 
                v.muted = true; 
                v.autoplay = true;
                v.play().catch(e => console.log(e)); 
            });
            
            // 策略2: 点击常见的播放按钮层
            var buttons = document.querySelectorAll('.vjs-big-play-button, .btn-play, .btn_play, button[title="Play"]');
            buttons.forEach(b => b.click());
        """)
        
        # 3. 循环等待网络请求
        print("⏳ 监控网络请求 (20秒)...")
        found_url = None
        target_domains = ['gscdn.kbs.co.kr', 'kbs.co.kr']
        
        for i in range(20):
            network_urls = extract_m3u8_from_network_logs(driver, target_domains)
            
            # 优先找带签名的
            valid_urls = [
                u for u in network_urls 
                if target_signature in u 
                and 'Policy=' in u
            ]
            
            if valid_urls:
                found_url = sorted(valid_urls, key=len, reverse=True)[0]
                print(f"⚡ 成功捕获链接！(耗时 {i}s)")
                break
            
            # 备选：如果不带特定签名但有Policy (应对域名变更)
            if i > 15:
                loose_urls = [u for u in network_urls if 'Policy=' in u and 'gscdn' in u]
                if loose_urls:
                    found_url = loose_urls[0]
                    break

            time.sleep(1)

        if found_url:
            print(f"✅ 找到地址")
            return found_url
            
        print(f"❌ 未找到有效地址")
        return None
            
    except Exception as e:
        print(f"❌ 出错: {str(e)}")
        return None

def get_real_mbn_url_from_response(auth_url):
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
        print("❌ 无Token")
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
    except:
        return False

def generate_playlist(dynamic_channels):
    lines = ["#EXTM3U", f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    later_channels = ['KBS DRAMA', 'KBS JOY', 'KBS STORY', 'KBS LIFE']
    
    for ch in dynamic_channels:
        if ch['name'] not in later_channels:
            lines.append(f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}",{ch["name"]}')
            lines.append(ch['url'])
            lines.append("")
            
    lines.extend(STATIC_CHANNELS)
    lines.append("")
    
    for ch in dynamic_channels:
        if ch['name'] in later_channels:
            lines.append(f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}",{ch["name"]}')
            lines.append(ch['url'])
            lines.append("")
            
    return "\n".join(lines)

def main():
    print("🎬 开始运行...")
    driver = setup_driver()
    channels_data = []
    
    try:
        for channel in CHANNELS:
            if channel['name'] == "MBN":
                channels_data.extend(get_mbn_m3u8_multiple_quality(driver))
            else:
                url = get_kbs_m3u8(driver, channel['url'], channel['name'])
                if url:
                    channels_data.append({
                        'name': channel['name'],
                        'tvg_id': channel['tvg_id'],
                        'url': url
                    })
        
        playlist = generate_playlist(channels_data)
        with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
            f.write(playlist)
        update_stable_repository(playlist)
        
        print(f"📊 完成！成功获取 {len(channels_data)} 个频道")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
