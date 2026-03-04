#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新GitHub仓库
简化版 - 聚焦网络日志轮询和页面参数提取
"""

import requests
import re
import time
import json
import os
import base64
from datetime import datetime
from typing import Optional, List
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
    {"name": "KBS1", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=11&ch_type=globalList", "tvg_id": "KBS1.kr"},
    {"name": "KBS2", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=12&ch_type=globalList", "tvg_id": "KBS2.kr"},
    {"name": "KBS 24", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=81&ch_type=globalList", "tvg_id": "KBS24.kr"},
    {"name": "MBN", "url": "https://www.mbn.co.kr/vod/onair", "tvg_id": "MBN.kr"},
    {"name": "KBS DRAMA", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N91&ch_type=globalList", "tvg_id": "KBSDRAMA.kr"},
    {"name": "KBS JOY", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N92&ch_type=globalList", "tvg_id": "KBSJOY.kr"},
    {"name": "KBS STORY", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N94&ch_type=globalList", "tvg_id": "KBSSTORY.kr"},
    {"name": "KBS LIFE", "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=N93&ch_type=globalList", "tvg_id": "KBSLIFE.kr"}
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
    """设置Chrome驱动（headless）"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def extract_m3u8_from_logs(driver, target_domains=None):
    """从性能日志中提取m3u8 URL"""
    urls = []
    try:
        logs = driver.get_log('performance')
        for log in logs:
            msg = json.loads(log['message'])['message']
            if msg['method'] in ['Network.requestWillBeSent', 'Network.responseReceived']:
                url = msg['params'].get('request', {}).get('url', '') or msg['params'].get('response', {}).get('url', '')
                if url and '.m3u8' in url:
                    if target_domains:
                        if any(d in url for d in target_domains):
                            urls.append(url)
                    else:
                        urls.append(url)
    except Exception as e:
        print(f"⚠️ 日志解析错误: {e}")
    return list(set(urls))

def wait_for_ad(driver, seconds=30):
    """等待广告（简单延时）"""
    print(f"⏳ 等待 {seconds} 秒（广告+缓冲）...")
    for i in range(seconds):
        time.sleep(1)
        if i % 5 == 0:
            print(f"  ... {i+1}/{seconds} 秒")

def get_kbs_m3u8(driver, channel_name, page_url):
    """获取KBS带参数的m3u8地址"""
    print(f"🎬 正在获取 {channel_name}...")
    driver.get(page_url)
    time.sleep(8)

    # 等待视频元素出现
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "video")))
        print("🎥 视频元素已出现")
    except:
        print("⚠️ 视频元素未出现，继续")

    # 尝试点击播放按钮（通用选择器）
    clicked = False
    for selector in ["button[class*='play']", "div[class*='play']", ".btn-play", ".play-button"]:
        elems = driver.find_elements(By.CSS_SELECTOR, selector)
        for el in elems:
            if el.is_displayed():
                driver.execute_script("arguments[0].click();", el)
                print(f"🖱️ 点击了 {selector}")
                clicked = True
                break
        if clicked:
            break
    if not clicked:
        driver.execute_script("document.querySelector('video')?.play();")
        print("🎬 直接调用 video.play()")

    # 等待广告
    wait_for_ad(driver, 30)

    # ---------- 方法1：长时间轮询网络日志（120秒） ----------
    print("📡 开始轮询网络日志（最长120秒）...")
    captured = []
    start = time.time()
    while time.time() - start < 120:
        new_urls = extract_m3u8_from_logs(driver, ['gscdn.kbs.co.kr'])
        for u in new_urls:
            if u not in captured:
                captured.append(u)
                print(f"📥 捕获到 m3u8: {u[:150]}...")
        # 如果找到带参数的，立即返回
        for u in captured:
            if 'Policy=' in u and 'Signature=' in u:
                print("✅ 找到带认证参数的URL")
                return u
        time.sleep(2)
        print("⏳ 等待中...")

    # 如果捕获到无参数的，也返回
    if captured:
        print("⚠️ 只捕获到基础URL，尝试使用")
        return captured[0]

    # ---------- 方法2：从页面源码提取Policy和Signature ----------
    print("🔍 尝试从页面源码提取 Policy 和 Signature...")
    html = driver.page_source
    # 先尝试匹配完整URL（万一有）
    full_match = re.search(r'(https?://[^\s"\']*gscdn\.kbs\.co\.kr[^\s"\']*\.m3u8\?[^\s"\']*Policy=[^\s"\']*Signature=[^\s"\']*)', html)
    if full_match:
        print("✅ 找到完整URL")
        return full_match.group(1)

    # 提取参数
    policy = re.search(r'Policy=([A-Za-z0-9_\-~]+)', html)
    signature = re.search(r'Signature=([A-Za-z0-9_\-~]+)', html)
    if policy and signature:
        base = KBS_BASE_URLS.get(channel_name)
        if base:
            key = "APKAICDSGT3Y7IXGJ3TA"  # 固定Key-Pair-Id
            final = f"{base}?Policy={policy.group(1)}&Key-Pair-Id={key}&Signature={signature.group(1)}"
            print("✅ 通过参数构造成功")
            return final
        else:
            print(f"❌ 未知频道 {channel_name} 的基础URL")

    # ---------- 最终备用 ----------
    print("❌ 所有方法失败，使用基础URL")
    return KBS_BASE_URLS.get(channel_name)

def get_mbn_m3u8_multiple_quality(driver):
    """获取MBN的双画质版本（已验证有效）"""
    print("🚀 正在获取 MBN 多画质版本...")
    driver.get("https://www.mbn.co.kr/vod/onair")
    time.sleep(15)
    logs = extract_m3u8_from_logs(driver, ['mbn.co.kr', 'hls-live.mbn.co.kr'])
    auth_urls = [u for u in logs if 'mbnStreamAuth' in u]

    def fetch_real(auth_url):
        try:
            resp = requests.get(auth_url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.mbn.co.kr/vod/onair'}, timeout=10)
            if resp.status_code == 200 and resp.text.startswith('http') and '.m3u8' in resp.text:
                return resp.text.strip()
        except:
            pass
        return None

    results = []
    for quality, name in [('1000k', 'MBN（高画质）'), ('600k', 'MBN（标清）')]:
        found = [u for u in auth_urls if quality in u]
        if found:
            real = fetch_real(found[0])
            if real:
                results.append({'name': name, 'tvg_id': 'MBN.kr', 'url': real})
                continue
        # 构造备用
        constructed = f"https://www.mbn.co.kr/player/mbnStreamAuth_new_live.mbn?vod_url=https://hls-live.mbn.co.kr/mbn-on-air/{quality}/playlist.m3u8"
        real = fetch_real(constructed)
        if real:
            results.append({'name': name, 'tvg_id': 'MBN.kr', 'url': real})
        else:
            # 最终备用
            results.append({'name': name, 'tvg_id': 'MBN.kr', 'url': f'https://hls-live.mbn.co.kr/mbn-on-air/{quality}/playlist.m3u8'})
    return results

def generate_playlist(dynamic_channels):
    """生成M3U文件"""
    lines = ["#EXTM3U", f"# 自动生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    later = ['KBS DRAMA', 'KBS JOY', 'KBS STORY', 'KBS LIFE']
    # 先放其他动态频道
    for ch in dynamic_channels:
        if ch['name'] not in later:
            lines.append(f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}",{ch["name"]}')
            lines.append(ch['url'])
            lines.append("")
    # 静态频道
    lines.extend(STATIC_CHANNELS)
    lines.append("")
    # 最后放指定的KBS
    for ch in dynamic_channels:
        if ch['name'] in later:
            lines.append(f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}",{ch["name"]}')
            lines.append(ch['url'])
            lines.append("")
    return "\n".join(lines)

def update_github(content):
    if not FULL_ACCESS_TOKEN:
        print("❌ 无GitHub Token，跳过")
        return False
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/contents/korean_tv.m3u"
    headers = {"Authorization": f"token {FULL_ACCESS_TOKEN}"}
    get_resp = requests.get(url, headers=headers)
    sha = get_resp.json().get('sha') if get_resp.status_code == 200 else None
    data = {
        "message": f"自动更新 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha
    } if sha else {
        "message": f"自动更新 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": base64.b64encode(content.encode()).decode()
    }
    resp = requests.put(url, headers=headers, json=data)
    if resp.status_code in [200, 201]:
        print("🎉 GitHub更新成功")
        return True
    else:
        print(f"❌ GitHub更新失败: {resp.status_code}")
        return False

def main():
    start = time.time()
    print("🎬 开始获取M3U8链接...")
    driver = setup_driver()
    dynamic = []

    for ch in CHANNELS:
        print(f"\n{'='*50}\n🔍 处理: {ch['name']}")
        if ch['name'] == 'MBN':
            mbn_list = get_mbn_m3u8_multiple_quality(driver)
            dynamic.extend(mbn_list)
        else:
            url = get_kbs_m3u8(driver, ch['name'], ch['url'])
            if url:
                dynamic.append({'name': ch['name'], 'tvg_id': ch['tvg_id'], 'url': url})
                print(f"✅ {ch['name']} 成功")
            else:
                print(f"❌ {ch['name']} 失败")

    playlist = generate_playlist(dynamic)
    with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
        f.write(playlist)
    print("💾 本地文件已保存")
    update_github(playlist)

    driver.quit()
    print(f"⏱️ 总耗时: {time.time()-start:.2f}秒")

if __name__ == "__main__":
    main()
