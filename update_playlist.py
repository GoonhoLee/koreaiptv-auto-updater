#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新Gist
"""

import requests
import re
import time
import json
import os
import urllib.parse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Gist配置 - 从环境变量读取Token
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
    'https://ytnlive.ytn.co.kr/ytn/_definst_/ytnlive_stream_20220426/medialist_9171188557012390620_hls.m3u8',
    '',
    '#EXTINF:-1 tvg-name="EBS 1 Ⓢ" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/EBS_1TV_Logo.svg/512px-EBS_1TV_Logo.svg.png" tvg-id="EBS1TV.kr" group-title="Korea",EBS 1 Ⓢ',
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
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 启用性能日志记录来捕获网络请求
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
                
                if method == 'Network.responseReceived':
                    response = message['params']['response']
                    url = response['url']
                    
                    # 检查是否是m3u8文件且来自目标域名
                    if '.m3u8' in url and any(domain in url for domain in target_domains):
                        m3u8_urls.append(url)
                        print(f"📡 从网络请求找到: {url}")
                        
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"⚠️ 读取网络日志时出错: {e}")
    
    return m3u8_urls

def get_kbs_m3u8(driver, url, channel_name):
    """获取KBS的m3u8链接 - 改进版"""
    try:
        print(f"🎬 正在获取 {channel_name}...")
        driver.get(url)
        
        # 等待页面加载和可能的广告
        print("⏳ 等待页面加载...")
        time.sleep(8)
        
        m3u8_urls = []
        target_domains = ['kbs.co.kr', 'gscdn.kbs.co.kr']
        
        # 方法1: 从网络请求中捕获真实的m3u8地址
        print("🔍 监控网络请求...")
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 方法2: 在页面源代码中搜索包含完整参数的m3u8链接
        print("🔍 搜索页面源代码...")
        page_source = driver.page_source
        
        # 改进的正则表达式，匹配完整的m3u8 URL（包含参数）
        m3u8_pattern = r'https?://[^\s"\']*\.m3u8(?:\?[^\s"\']*)?'
        source_urls = re.findall(m3u8_pattern, page_source)
        
        # 过滤出KBS相关的m3u8链接
        kbs_urls = [url for url in source_urls if any(domain in url for domain in target_domains)]
        m3u8_urls.extend(kbs_urls)
        
        # 方法3: 查找JavaScript变量中的m3u8链接
        print("🔍 检查JavaScript变量...")
        try:
            script_elements = driver.find_elements(By.TAG_NAME, 'script')
            for script in script_elements:
                script_content = script.get_attribute('innerHTML')
                if script_content:
                    script_urls = re.findall(m3u8_pattern, script_content)
                    kbs_script_urls = [url for url in script_urls if any(domain in url for domain in target_domains)]
                    m3u8_urls.extend(kbs_script_urls)
        except Exception as e:
            print(f"⚠️ 检查JavaScript时出错: {e}")
        
        # 方法4: 尝试点击播放按钮（如果有）
        try:
            print("🔍 查找播放按钮...")
            play_buttons = driver.find_elements(By.XPATH, "//button[contains(., '재생') or contains(., 'Play') or contains(., '시작')]")
            for button in play_buttons[:2]:  # 只尝试前两个按钮
                try:
                    button.click()
                    time.sleep(3)
                    # 点击后再次捕获网络请求
                    new_urls = extract_m3u8_from_network_logs(driver, target_domains)
                    m3u8_urls.extend(new_urls)
                except:
                    continue
        except Exception as e:
            print(f"⚠️ 点击播放按钮时出错: {e}")
        
        # 去重并选择最佳的m3u8链接
        unique_urls = list(set(m3u8_urls))
        
        if unique_urls:
            # 优先选择包含完整参数的URL（通常是真实的直播地址）
            param_urls = [url for url in unique_urls if '?' in url and 'Expires=' in url]
            if param_urls:
                selected_url = param_urls[0]
            else:
                selected_url = unique_urls[0]
            
            print(f"✅ 找到 {channel_name} 真实m3u8地址: {selected_url}")
            return selected_url
        else:
            print(f"❌ 未找到 {channel_name} 的真实m3u8地址，使用静态地址")
            # 返回静态地址
            if "1TV" in channel_name:
                return "https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8"
            elif "2TV" in channel_name:
                return "https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8"
            return None
            
    except Exception as e:
        print(f"❌ 获取 {channel_name} 时出错: {str(e)}")
        return None

def get_mbn_m3u8(driver):
    """获取MBN的m3u8链接 - 改进版"""
    try:
        print("🚀 正在获取 MBN...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        
        # 等待页面加载
        print("⏳ 等待MBN页面加载...")
        time.sleep(12)
        
        m3u8_urls = []
        target_domains = ['mbn.co.kr']
        
        # 方法1: 从网络请求中捕获真实的m3u8地址
        print("🔍 监控网络请求...")
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 方法2: 在页面源代码中搜索
        print("🔍 搜索页面源代码...")
        page_source = driver.page_source
        m3u8_pattern = r'https?://[^\s"\']*\.m3u8(?:\?[^\s"\']*)?'
        source_urls = re.findall(m3u8_pattern, page_source)
        mbn_urls = [url for url in source_urls if any(domain in url for domain in target_domains)]
        m3u8_urls.extend(mbn_urls)
        
        # 方法3: 查找视频播放器
        print("🔍 查找视频播放器...")
        video_elements = driver.find_elements(By.TAG_NAME, 'video')
        for video in video_elements:
            src = video.get_attribute('src')
            if src and '.m3u8' in src:
                m3u8_urls.append(src)
                print(f"🎥 从video标签找到: {src}")
        
        # 方法4: 查找source标签
        source_elements = driver.find_elements(By.TAG_NAME, 'source')
        for source in source_elements:
            src = source.get_attribute('src')
            if src and '.m3u8' in src:
                m3u8_urls.append(src)
                print(f"📹 从source标签找到: {src}")
        
        # 去重并选择最佳的m3u8链接
        unique_urls = list(set(m3u8_urls))
        
        if unique_urls:
            # 优先选择包含完整参数的URL
            param_urls = [url for url in unique_urls if '?' in url]
            if param_urls:
                selected_url = param_urls[0]
            else:
                selected_url = unique_urls[0]
            
            print(f"✅ 找到 MBN 真实m3u8地址: {selected_url}")
            return selected_url
        else:
            print("❌ 未找到 MBN 的真实m3u8地址，使用备用地址")
            return "https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8"
            
    except Exception as e:
        print(f"❌ 获取 MBN 时出错: {str(e)}")
        return "https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8"

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
            print(f"❌ Gist更新失败: {response.status_code} - {response.text}")
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
        
        # 获取MBN
        mbn_url = get_mbn_m3u8(driver)
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
        
        # 同时保存到本地文件
        with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
            f.write(playlist_content)
        print("💾 播放列表已保存到 korean_tv.m3u")
        
        # 打印统计信息
        successful_channels = [ch for ch in dynamic_channels if ch.get('url')]
        print(f"📊 成功获取 {len(successful_channels)}/{len(dynamic_channels)} 个频道的m3u8链接")
        
    except Exception as e:
        print(f"❌ 执行过程中出错: {str(e)}")
    finally:
        if driver:
            print("🔚 关闭浏览器驱动...")
            driver.quit()

if __name__ == "__main__":
    main()
