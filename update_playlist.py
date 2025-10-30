#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新Gist
优先获取高清版本
"""

import requests
import re
import time
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Gist配置
GIST_ID = "1eefb097a9b3ec25c79bbd4149066d41"
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

# 电视台配置
CHANNELS = [
    {
        "name": "KBS 1TV",
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=11&ch_type=globalList",
        "tvg_id": "KBS1TV.kr"
    },
    {
        "name": "KBS 2TV", 
        "url": "https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=12&ch_type=globalList",
        "tvg_id": "KBS2TV.kr"
    },
    {
        "name": "MBN",
        "url": "https://www.mbn.co.kr/vod/onair",
        "tvg_id": "MBN.kr"
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
    'https://ytnlive.ytn.co.kr/ytn/_definst_/ytnlive_stream_20220426/medialist_9171188557012390620_hls.m3u8'
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
    """获取KBS的m3u8链接"""
    try:
        print(f"🎬 正在获取 {channel_name}...")
        driver.get(url)
        time.sleep(12)
        
        m3u8_urls = []
        target_domains = ['kbs.co.kr', 'gscdn.kbs.co.kr']
        
        # 网络请求监控
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 如果没找到，刷新重试
        if not m3u8_urls:
            print("🔄 刷新页面重新尝试...")
            driver.refresh()
            time.sleep(8)
            network_urls = extract_m3u8_from_network_logs(driver, target_domains)
            m3u8_urls.extend(network_urls)
        
        # 页面源代码搜索
        page_source = driver.page_source
        m3u8_pattern = r'https?://[^\s"\']*\.m3u8(?:\?[^\s"\']*)?'
        source_urls = re.findall(m3u8_pattern, page_source)
        kbs_urls = [url for url in source_urls if any(domain in url for domain in target_domains)]
        m3u8_urls.extend(kbs_urls)
        
        # 去重并选择
        unique_urls = list(set(m3u8_urls))
        
        if unique_urls:
            # 优先选择包含认证参数的URL
            auth_urls = [url for url in unique_urls if '?' in url and any(param in url for param in ['Expires=', 'Policy=', 'Signature='])]
            selected_url = auth_urls[0] if auth_urls else unique_urls[0]
            
            print(f"✅ 找到 {channel_name} 真实地址")
            return selected_url
        else:
            print(f"❌ 未找到 {channel_name} 地址，使用静态地址")
            return "https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8" if "1TV" in channel_name else "https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8"
            
    except Exception as e:
        print(f"❌ 获取 {channel_name} 时出错: {str(e)}")
        return None

def get_real_mbn_url_from_response(auth_url):
    """从MBN认证链接的响应内容获取真实m3u8地址"""
    try:
        print(f"🔗 请求MBN认证链接: {auth_url}")
        
        # 设置请求头，模拟浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.mbn.co.kr/vod/onair'
        }
        
        response = requests.get(auth_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # 获取响应内容
            content = response.text.strip()
            
            # 检查响应内容是否是有效的m3u8 URL
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

def get_mbn_m3u8_hd(driver):
    """获取MBN的m3u8链接 - 优先高清版本"""
    try:
        print("🚀 正在获取 MBN...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        time.sleep(15)
        
        m3u8_urls = []
        target_domains = ['mbn.co.kr', 'hls-live.mbn.co.kr']
        
        # 网络请求监控 - 查找认证链接
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 查找所有认证代理链接，优先选择高清版本
        auth_urls = [url for url in m3u8_urls if 'mbnStreamAuth' in url]
        
        # 优先选择1000k高清版本
        hd_auth_urls = [url for url in auth_urls if '1000k' in url]
        sd_auth_urls = [url for url in auth_urls if '600k' in url]
        
        # 尝试高清版本
        if hd_auth_urls:
            print(f"🔍 找到MBN高清认证链接: {hd_auth_urls[0]}")
            real_url = get_real_mbn_url_from_response(hd_auth_urls[0])
            if real_url:
                print("🎯 成功获取高清版本 (1000k)")
                return real_url
        
        # 如果高清版本失败，尝试标清版本
        if sd_auth_urls:
            print(f"🔍 找到MBN标清认证链接: {sd_auth_urls[0]}")
            real_url = get_real_mbn_url_from_response(sd_auth_urls[0])
            if real_url:
                print("📺 使用标清版本 (600k)")
                return real_url
        
        # 如果自动发现的链接都失败，尝试直接构造高清认证链接
        print("🔄 尝试构造高清认证链接...")
        hd_base_url = "https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8"
        constructed_hd_auth_url = f"https://www.mbn.co.kr/player/mbnStreamAuth_new_live.mbn?vod_url={hd_base_url}"
        
        print(f"🔧 尝试构造的高清认证链接: {constructed_hd_auth_url}")
        real_url = get_real_mbn_url_from_response(constructed_hd_auth_url)
        if real_url:
            print("🎯 通过构造链接获取高清版本 (1000k)")
            return real_url
        
        # 如果高清构造失败，尝试标清构造
        print("🔄 尝试构造标清认证链接...")
        sd_base_url = "https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8"
        constructed_sd_auth_url = f"https://www.mbn.co.kr/player/mbnStreamAuth_new_live.mbn?vod_url={sd_base_url}"
        
        print(f"🔧 尝试构造的标清认证链接: {constructed_sd_auth_url}")
        real_url = get_real_mbn_url_from_response(constructed_sd_auth_url)
        if real_url:
            print("📺 通过构造链接获取标清版本 (600k)")
            return real_url
        
        print("❌ 所有方法都失败，使用备用高清地址")
        return "https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8"
            
    except Exception as e:
        print(f"❌ 获取 MBN 时出错: {str(e)}")
        return "https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8"

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
    print("🎬 开始获取M3U8链接...")
    
    driver = None
    try:
        driver = setup_driver()
        dynamic_channels = []
        
        # 获取KBS 1TV
        kbs1_url = get_kbs_m3u8(driver, CHANNELS[0]['url'], CHANNELS[0]['name'])
        dynamic_channels.append({
            'name': CHANNELS[0]['name'],
            'tvg_id': CHANNELS[0]['tvg_id'],
            'url': kbs1_url
        })
        
        # 获取KBS 2TV
        kbs2_url = get_kbs_m3u8(driver, CHANNELS[1]['url'], CHANNELS[1]['name'])
        dynamic_channels.append({
            'name': CHANNELS[1]['name'],
            'tvg_id': CHANNELS[1]['tvg_id'],
            'url': kbs2_url
        })
        
        # 获取MBN - 使用高清优先版
        mbn_url = get_mbn_m3u8_hd(driver)
        dynamic_channels.append({
            'name': CHANNELS[2]['name'],
            'tvg_id': CHANNELS[2]['tvg_id'],
            'url': mbn_url
        })
        
        # 生成播放列表
        playlist_content = generate_playlist(dynamic_channels)
        print("✅ 播放列表生成完成!")
        
        # 更新Gist
        update_gist(playlist_content)
        
        # 保存到本地文件
        with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
            f.write(playlist_content)
        print("💾 播放列表已保存到 korean_tv.m3u")
        
        # 打印统计
        successful_channels = [ch for ch in dynamic_channels if ch.get('url')]
        print(f"📊 成功获取 {len(successful_channels)}/{len(dynamic_channels)} 个频道")
        
    except Exception as e:
        print(f"❌ 执行过程中出错: {str(e)}")
    finally:
        if driver:
            print("🔚 关闭浏览器驱动...")
            driver.quit()

if __name__ == "__main__":
    main()
