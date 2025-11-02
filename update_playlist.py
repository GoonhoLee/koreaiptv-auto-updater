#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新Gist和固定仓库
优化版本 - 支持多频道自动抓取
"""

import requests
import re
import time
import json
import os
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 配置信息
GITHUB_USERNAME = "GoonhoLee"
STABLE_REPO_NAME = "korean-tv-static"
GIST_ID = "1eefb097a9b3ec25c79bbd4149066d41"
FULL_ACCESS_TOKEN = os.getenv('FULL_ACCESS_TOKEN')
GITHUB_TOKEN = FULL_ACCESS_TOKEN

# 电视台配置 - 新增SBS和MBC频道
CHANNELS = [
    # KBS频道
    {
        "name": "KBS 1TV",
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=11&ch_type=globalList",
        "tvg_id": "KBS1TV.kr",
        "type": "kbs"
    },
    {
        "name": "KBS 2TV", 
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=12&ch_type=globalList",
        "tvg_id": "KBS2TV.kr",
        "type": "kbs"
    },
    # MBN频道
    {
        "name": "MBN",
        "url": "https://www.mbn.co.kr/vod/onair",
        "tvg_id": "MBN.kr",
        "type": "mbn"
    },
    # SBS频道
    {
        "name": "SBS",
        "url": "https://www.sbs.co.kr/live/S01?div=live_list",
        "tvg_id": "SBS.kr",
        "type": "sbs"
    },
    {
        "name": "SBS PLUS",
        "url": "https://www.sbs.co.kr/live/S03?div=live_end", 
        "tvg_id": "SBSPLUS.kr",
        "type": "sbs"
    },
    {
        "name": "SBS funE",
        "url": "https://www.sbs.co.kr/live/S04?div=live_end",
        "tvg_id": "SBSfunE.kr",
        "type": "sbs"
    },
    # MBC频道
    {
        "name": "MBC",
        "url": "https://onair.imbc.com/",
        "tvg_id": "MBC.kr",
        "type": "mbc"
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
    '#EXTINF:-1 tvg-name="EBS 1 Ⓢ" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/EBS_1TV_Logo.svg/512px-EBS_1TV_Logo.svg.png" tvg-id="EBS1TV.kr" group-title="Korea",EBS 1 Ⓢ',
    'https://ebsonair.ebs.co.kr/ebs1familypc/familypc1m/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-name="EBS 2 Ⓢ" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/EBS_2TV_Logo.svg/512px-EBS_2TV_Logo.svg.png" tvg-id="EBS2TV.kr" group-title="Korea",EBS 2 Ⓢ',
    'https://ebsonair.ebs.co.kr/ebs2familypc/familypc1m/playlist.m3u8'
]

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    driver = webdriver.Chrome(options=chrome_options)
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

def get_kbs_m3u8(driver, url, channel_name):
    """获取KBS的m3u8链接 - 优化版本"""
    try:
        print(f"🎬 正在获取 {channel_name}...")
        
        driver.get(url)
        time.sleep(8)  # 减少等待时间
        
        target_domains = ['kbs.co.kr', 'gscdn.kbs.co.kr']
        m3u8_urls = []
        
        # 网络请求监控
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 页面源代码搜索
        page_source = driver.page_source
        m3u8_pattern = r'https?://[^\s"\']*\.m3u8(?:\?[^\s"\']*)?'
        source_urls = re.findall(m3u8_pattern, page_source)
        kbs_urls = [url for url in source_urls if any(domain in url for domain in target_domains)]
        m3u8_urls.extend(kbs_urls)
        
        # 智能选择URL
        unique_urls = list(set(m3u8_urls))
        
        if unique_urls:
            # 优先选择包含认证参数的URL
            auth_urls = [url for url in unique_urls if '?' in url and any(param in url for param in ['Expires=', 'Policy=', 'Signature='])]
            if auth_urls:
                selected_url = auth_urls[0]
            else:
                selected_url = unique_urls[0]
            
            print(f"✅ 找到 {channel_name}: {selected_url[:80]}...")
            return selected_url
        else:
            print(f"❌ 未找到 {channel_name}，使用静态地址")
            return f"https://{'1tv' if '1TV' in channel_name else '2tv'}.gscdn.kbs.co.kr/{'1tv' if '1TV' in channel_name else '2tv'}_1.m3u8"
            
    except Exception as e:
        print(f"❌ 获取 {channel_name} 时出错: {str(e)}")
        return None

def get_mbn_m3u8(driver):
    """获取MBN的m3u8链接 - 简化版本"""
    try:
        print("🎬 正在获取 MBN...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        time.sleep(8)
        
        target_domains = ['mbn.co.kr', 'hls-live.mbn.co.kr']
        m3u8_urls = extract_m3u8_from_network_logs(driver, target_domains)
        
        # 查找认证链接
        auth_urls = [url for url in m3u8_urls if 'mbnStreamAuth' in url]
        
        if auth_urls:
            # 使用第一个认证链接获取真实地址
            auth_url = auth_urls[0]
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
                'Referer': 'https://www.mbn.co.kr/vod/onair'
            }
            
            response = requests.get(auth_url, headers=headers, timeout=10)
            if response.status_code == 200:
                content = response.text.strip()
                if content.startswith('http') and '.m3u8' in content:
                    print(f"✅ 找到 MBN: {content[:80]}...")
                    return content
        
        # 备用地址
        backup_url = "https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8"
        print(f"⚠️ 使用MBN备用地址: {backup_url}")
        return backup_url
            
    except Exception as e:
        print(f"❌ 获取 MBN 时出错: {str(e)}")
        return "https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8"

def get_sbs_m3u8(driver, url, channel_name):
    """获取SBS频道的m3u8链接"""
    try:
        print(f"🎬 正在获取 {channel_name}...")
        
        driver.get(url)
        time.sleep(8)
        
        target_domains = ['sbs.co.kr', 'apisbs.sbs.co.kr', 'sbs-cdn.com']
        m3u8_urls = []
        
        # 网络请求监控
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 页面源代码搜索
        page_source = driver.page_source
        m3u8_pattern = r'https?://[^\s"\']*\.m3u8(?:\?[^\s"\']*)?'
        source_urls = re.findall(m3u8_pattern, page_source)
        sbs_urls = [url for url in source_urls if any(domain in url for domain in target_domains)]
        m3u8_urls.extend(sbs_urls)
        
        # 查找视频播放器相关的URL
        video_patterns = [
            r'videoUrl["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'src["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'
        ]
        
        for pattern in video_patterns:
            matches = re.findall(pattern, page_source)
            for match in matches:
                if any(domain in match for domain in target_domains):
                    m3u8_urls.append(match)
        
        unique_urls = list(set(m3u8_urls))
        
        if unique_urls:
            selected_url = unique_urls[0]
            print(f"✅ 找到 {channel_name}: {selected_url[:80]}...")
            return selected_url
        else:
            print(f"❌ 未找到 {channel_name} 的m3u8地址")
            return None
            
    except Exception as e:
        print(f"❌ 获取 {channel_name} 时出错: {str(e)}")
        return None

def get_mbc_m3u8(driver, url, channel_name):
    """获取MBC的m3u8链接"""
    try:
        print(f"🎬 正在获取 {channel_name}...")
        
        driver.get(url)
        time.sleep(8)
        
        target_domains = ['imbc.com', 'mbc.co.kr', 'sticky.mbc.co.kr']
        m3u8_urls = []
        
        # 网络请求监控
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 页面源代码搜索
        page_source = driver.page_source
        m3u8_pattern = r'https?://[^\s"\']*\.m3u8(?:\?[^\s"\']*)?'
        source_urls = re.findall(m3u8_pattern, page_source)
        mbc_urls = [url for url in source_urls if any(domain in url for domain in target_domains)]
        m3u8_urls.extend(mbc_urls)
        
        # 尝试查找MBC特定的播放器配置
        mbc_patterns = [
            r'streamUrl["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'videoSrc["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'filePath["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'
        ]
        
        for pattern in mbc_patterns:
            matches = re.findall(pattern, page_source)
            for match in matches:
                if any(domain in match for domain in target_domains):
                    m3u8_urls.append(match)
        
        unique_urls = list(set(m3u8_urls))
        
        if unique_urls:
            selected_url = unique_urls[0]
            print(f"✅ 找到 {channel_name}: {selected_url[:80]}...")
            return selected_url
        else:
            print(f"❌ 未找到 {channel_name} 的m3u8地址")
            return None
            
    except Exception as e:
        print(f"❌ 获取 {channel_name} 时出错: {str(e)}")
        return None

def update_gist(content):
    """更新Gist内容"""
    if not GITHUB_TOKEN:
        print("❌ 未找到GITHUB_TOKEN，跳过Gist更新")
        return False
        
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {
        "description": f"韩国电视台直播源 - 更新时间 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "files": {
            "korean_tv.m3u": {
                "content": content
            }
        }
    }
    
    try:
        print("📝 正在更新Gist...")
        response = requests.patch(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print("✅ Gist更新成功!")
            return True
        else:
            print(f"❌ Gist更新失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 更新Gist时出错: {str(e)}")
        return False

def update_stable_repository(content):
    """更新固定仓库的M3U文件"""
    if not GITHUB_TOKEN:
        print("❌ 未找到GITHUB_TOKEN，跳过固定仓库更新")
        return False
        
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/contents/korean_tv.m3u"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # 获取文件当前SHA
        response = requests.get(url, headers=headers)
        sha = None
        if response.status_code == 200:
            sha = response.json().get('sha')
        
        # Base64编码
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('ascii')
        
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
            print("🎉 固定仓库更新成功!")
            static_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/main/korean_tv.m3u"
            print(f"🔗 您的静态URL是: {static_url}")
            return True
        else:
            print(f"❌ 固定仓库更新失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 更新固定仓库时出错: {str(e)}")
        return False

def generate_playlist(dynamic_channels):
    """生成完整的M3U播放列表"""
    lines = ["#EXTM3U"]
    lines.append(f"# 自动生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 添加动态获取的频道
    for channel in dynamic_channels:
        if channel.get('url'):
            lines.append(f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}",{channel["name"]}')
            lines.append(channel['url'])
            lines.append("")
    
    # 添加静态频道
    lines.extend(STATIC_CHANNELS)
    
    return "\n".join(lines)

def main():
    """主函数"""
    print("🎬 开始获取韩国电视台M3U8链接...")
    
    driver = None
    try:
        driver = setup_driver()
        dynamic_channels = []
        
        # 遍历所有频道
        for channel in CHANNELS:
            m3u8_url = None
            
            if channel['type'] == 'kbs':
                m3u8_url = get_kbs_m3u8(driver, channel['url'], channel['name'])
            elif channel['type'] == 'mbn':
                m3u8_url = get_mbn_m3u8(driver)
            elif channel['type'] == 'sbs':
                m3u8_url = get_sbs_m3u8(driver, channel['url'], channel['name'])
            elif channel['type'] == 'mbc':
                m3u8_url = get_mbc_m3u8(driver, channel['url'], channel['name'])
            
            if m3u8_url:
                dynamic_channels.append({
                    'name': channel['name'],
                    'tvg_id': channel['tvg_id'],
                    'url': m3u8_url
                })
            else:
                print(f"⚠️ 跳过 {channel['name']} - 未获取到有效URL")
        
        # 生成播放列表
        playlist_content = generate_playlist(dynamic_channels)
        print("✅ 播放列表生成完成!")
        
        # 更新Gist和固定仓库
        update_gist(playlist_content)
        update_stable_repository(playlist_content)
        
        # 保存到本地文件
        with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
            f.write(playlist_content)
        print("💾 播放列表已保存到 korean_tv.m3u")
        
        # 打印统计信息
        successful_channels = [ch for ch in dynamic_channels if ch.get('url')]
        print(f"\n📊 任务完成! 成功获取 {len(successful_channels)}/{len(CHANNELS)} 个频道")
        
        for channel in successful_channels:
            print(f"  ✅ {channel['name']}")
        
    except Exception as e:
        print(f"❌ 执行过程中出错: {str(e)}")
    finally:
        if driver:
            print("🔚 关闭浏览器驱动...")
            driver.quit()

if __name__ == "__main__":
    main()
