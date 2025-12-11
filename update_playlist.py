#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新GitHub仓库
修复KBS抓取问题：添加强制自动播放策略、鼠标物理点击模拟
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
from selenium.webdriver.common.action_chains import ActionChains
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
    """设置Chrome驱动 - 针对视频播放进行深度优化"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # === 关键修复：解决自动播放和Headless检测 ===
    # 允许无需用户交互的自动播放
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    # 静音音频（浏览器通常允许静音视频自动播放）
    chrome_options.add_argument("--mute-audio")
    
    # 模拟真实浏览器
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    # 移除自动化特征
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 开启性能日志
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # CDP命令防止检测
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
                            # 如果有域名限制，则检查
                            if not target_domains or any(domain in url for domain in target_domains):
                                m3u8_urls.append(url)
                            
            except Exception:
                continue
                
    except Exception as e:
        print(f"⚠️ 读取网络日志时出错: {e}")
    
    return list(set(m3u8_urls))

def get_kbs_m3u8(driver: webdriver.Chrome, url: str, channel_name: str) -> Optional[str]:
    """获取KBS的m3u8链接 - 针对15秒广告和播放触发优化"""
    try:
        print(f"🎬 正在获取 {channel_name}...")
        
        # 特征码映射
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
        time.sleep(3) # 等待页面基础加载
        
        # === 动作1：尝试物理点击播放器中心 ===
        # 很多播放器有透明覆盖层，直接点击 video 标签无效
        # 我们寻找页面上几个可能的容器，点击它们的中心
        print("🖱️ 尝试物理点击播放器中心...")
        try:
            # KBS 播放器容器常见的 class/id
            containers = driver.find_elements(By.CSS_SELECTOR, "#player, .player-area, .video-container, video")
            if containers:
                # 只点击第一个可见的
                action = ActionChains(driver)
                action.move_to_element(containers[0]).click().perform()
                print("  ✅ 已发送点击指令")
            else:
                # 如果找不到特定容器，点击页面中心
                action = ActionChains(driver)
                action.move_by_offset(960, 540).click().perform() # 假设1920x1080分辨率
                print("  ✅ 已点击屏幕中心")
        except Exception as e:
            print(f"  ⚠️ 点击操作异常 (不影响继续): {e}")

        # === 动作2：智能循环等待 (最多25秒) ===
        print("⏳ 正在监控网络请求 (等待广告结束)...")
        
        found_url = None
        target_domains = ['gscdn.kbs.co.kr', 'kbs.co.kr']
        
        # 每秒检查一次日志，而不是死等
        for i in range(25):
            network_urls = extract_m3u8_from_network_logs(driver, target_domains)
            
            # 过滤策略
            valid_urls = [
                u for u in network_urls 
                if target_signature in u 
                and 'Policy=' in u
            ]
            
            if valid_urls:
                # 找到链接，立即停止等待
                found_url = sorted(valid_urls, key=len, reverse=True)[0]
                print(f"⚡ 在第 {i+1} 秒成功捕获链接！")
                break
            
            time.sleep(1)
            if i % 5 == 0 and i > 0:
                print(f"  ...已等待 {i} 秒")

        if found_url:
            print(f"✅ 找到 {channel_name} 真实地址")
            return found_url
            
        # 如果还是没找到，打印一些调试信息
        print(f"❌ 超时未找到 {channel_name} 的有效地址")
        
        # 检查是否因为地域限制
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "not available" in page_text.lower() or "service region" in page_text.lower() or "해외" in page_text:
            print("🚫 警告：页面包含地域限制提示，可能是IP问题")

        return None
            
    except Exception as e:
        print(f"❌ 获取 {channel_name} 时出错: {str(e)}")
        return None

def get_real_mbn_url_from_response(auth_url):
    """从MBN认证链接的响应内容获取真实m3u8地址"""
    try:
        print(f"🔗 请求MBN认证链接: {auth_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.mbn.co.kr/vod/onair'
        }
        response = requests.get(auth_url, headers=headers, timeout=10)
        if response.status_code == 200:
            content = response.text.strip()
            if '.m3u8' in content:
                print(f"✅ 获取到MBN地址")
                return content
        return None
    except Exception as e:
        print(f"❌ MBN认证出错: {e}")
        return None

def get_mbn_m3u8_multiple_quality(driver):
    """获取MBN的m3u8链接 - 双画质"""
    mbn_channels = []
    try:
        print("🚀 正在获取 MBN 多画质版本...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        time.sleep(15) # MBN比较简单，固定等待即可
        
        m3u8_urls = extract_m3u8_from_network_logs(driver, ['mbn.co.kr'])
        auth_urls = [url for url in m3u8_urls if 'mbnStreamAuth' in url]
        
        configs = [
            {'q': '1000k', 'name': 'MBN（高画质）', 'base': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8'},
            {'q': '600k',  'name': 'MBN（标清）',   'base': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8'}
        ]
        
        for cfg in configs:
            real_url = None
            # 1. 尝试自动发现的认证链接
            valid_auths = [u for u in auth_urls if cfg['q'] in u]
            if valid_auths:
                real_url = get_real_mbn_url_from_response(valid_auths[0])
            
            # 2. 构造认证链接
            if not real_url:
                auth_url = f"https://www.mbn.co.kr/player/mbnStreamAuth_new_live.mbn?vod_url={cfg['base']}"
                real_url = get_real_mbn_url_from_response(auth_url)
                
            if real_url:
                mbn_channels.append({
                    'name': cfg['name'],
                    'tvg_id': 'MBN.kr',
                    'url': real_url
                })
                
        return mbn_channels
    except Exception as e:
        print(f"❌ MBN获取出错: {e}")
        return []

def update_stable_repository(content):
    """更新GitHub"""
    if not FULL_ACCESS_TOKEN:
        print("❌ 无Token，跳过更新")
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
        print(f"❌ GitHub更新出错: {e}")
        return False

def generate_playlist(dynamic_channels):
    """生成M3U"""
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
