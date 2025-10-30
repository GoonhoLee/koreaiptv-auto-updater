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
    """从网络日志中提取m3u8链接 - 增强版"""
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
                
                # 同时监控请求发送阶段
                elif method == 'Network.requestWillBeSent':
                    request = message['params']['request']
                    url = request['url']
                    if '.m3u8' in url and any(domain in url for domain in target_domains):
                        m3u8_urls.append(url)
                        print(f"📡 从网络请求发送找到: {url}")
                        
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"⚠️ 读取网络日志时出错: {e}")
    
    return m3u8_urls

def get_kbs_m3u8_enhanced(driver, url, channel_name):
    """获取KBS的m3u8链接 - 专门优化KBS1"""
    try:
        print(f"🎬 正在获取 {channel_name}...")
        
        # 清除之前的网络日志
        driver.get_log('performance')
        
        driver.get(url)
        
        # 更长的等待时间，确保视频播放器完全加载
        print("⏳ 等待KBS播放器完全加载...")
        time.sleep(15)
        
        m3u8_urls = []
        target_domains = ['kbs.co.kr', 'gscdn.kbs.co.kr']
        
        # 方法1: 深度网络请求监控
        print("🔍 深度监控网络请求...")
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 如果没找到，尝试刷新页面重新监控
        if not m3u8_urls:
            print("🔄 首次未找到，刷新页面重新尝试...")
            driver.refresh()
            time.sleep(10)
            network_urls = extract_m3u8_from_network_logs(driver, target_domains)
            m3u8_urls.extend(network_urls)
        
        # 方法2: 深度搜索页面源代码
        print("🔍 深度搜索页面源代码...")
        page_source = driver.page_source
        
        # 更全面的m3u8 URL匹配
        m3u8_patterns = [
            r'https?://[^\s"\']*\.m3u8(?:\?[^\s"\']*)?',
            r'["\'](https?://[^"\']*\.m3u8[^"\']*)["\']',
            r'url\(["\']?(https?://[^"\']*\.m3u8[^"\']*)["\']?\)'
        ]
        
        for pattern in m3u8_patterns:
            source_urls = re.findall(pattern, page_source)
            kbs_urls = [url for url in source_urls if any(domain in url for domain in target_domains)]
            m3u8_urls.extend(kbs_urls)
        
        # 方法3: 深度JavaScript分析
        print("🔍 深度分析JavaScript...")
        try:
            # 执行JavaScript来获取可能的视频源
            scripts = [
                "Array.from(document.querySelectorAll('video')).map(v => v.src).filter(src => src && src.includes('.m3u8'))",
                "Array.from(document.querySelectorAll('source')).map(s => s.src).filter(src => src && src.includes('.m3u8'))",
                "Object.values(window).filter(val => typeof val === 'string' && val.includes('.m3u8') && val.includes('kbs'))",
            ]
            
            for script in scripts:
                try:
                    result = driver.execute_script(f"return {script}")
                    if result and isinstance(result, list):
                        valid_urls = [url for url in result if any(domain in url for domain in target_domains)]
                        m3u8_urls.extend(valid_urls)
                        if valid_urls:
                            print(f"💻 从JS执行找到: {valid_urls}")
                except:
                    continue
                    
        except Exception as e:
            print(f"⚠️ 执行JavaScript时出错: {e}")
        
        # 方法4: 智能按钮点击
        print("🔍 智能查找播放按钮...")
        play_selectors = [
            "button", 
            ".btn-play", 
            ".play-button",
            "[onclick*='play']",
            "[class*='play']",
            "a[href*='javascript']"
        ]
        
        for selector in play_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements[:3]:  # 只尝试前几个
                    try:
                        text = element.text.lower()
                        if any(keyword in text for keyword in ['play', '재생', '시작', '보기']):
                            print(f"🖱️ 尝试点击播放按钮: {text}")
                            driver.execute_script("arguments[0].click();", element)
                            time.sleep(5)
                            # 点击后再次监控网络
                            new_urls = extract_m3u8_from_network_logs(driver, target_domains)
                            m3u8_urls.extend(new_urls)
                    except:
                        continue
            except Exception as e:
                continue
        
        # 方法5: 处理iframe
        print("🔍 检查iframe...")
        try:
            iframes = driver.find_elements(By.TAG_NAME, 'iframe')
            for i, iframe in enumerate(iframes):
                try:
                    print(f"  检查iframe {i+1}/{len(iframes)}")
                    driver.switch_to.frame(iframe)
                    time.sleep(3)
                    
                    # 检查iframe内的资源
                    iframe_source = driver.page_source
                    for pattern in m3u8_patterns:
                        iframe_urls = re.findall(pattern, iframe_source)
                        kbs_iframe_urls = [url for url in iframe_urls if any(domain in url for domain in target_domains)]
                        m3u8_urls.extend(kbs_iframe_urls)
                    
                    # 检查iframe内的视频元素
                    iframe_videos = driver.find_elements(By.TAG_NAME, 'video')
                    for video in iframe_videos:
                        src = video.get_attribute('src')
                        if src and '.m3u8' in src and any(domain in src for domain in target_domains):
                            m3u8_urls.append(src)
                    
                    driver.switch_to.default_content()
                except Exception as e:
                    driver.switch_to.default_content()
                    continue
        except Exception as e:
            print(f"⚠️ 检查iframe时出错: {e}")
            driver.switch_to.default_content()
        
        # 去重并智能选择
        unique_urls = list(set(m3u8_urls))
        
        if unique_urls:
            print(f"📊 找到 {len(unique_urls)} 个可能的m3u8链接")
            
            # 智能选择最佳URL
            # 优先选择包含认证参数的URL
            auth_urls = [url for url in unique_urls if '?' in url and any(param in url for param in ['Expires=', 'Policy=', 'Signature='])]
            if auth_urls:
                selected_url = auth_urls[0]
                print(f"✅ 找到 {channel_name} 真实认证地址")
            # 其次选择包含频道标识的URL
            elif "1TV" in channel_name:
                tv1_urls = [url for url in unique_urls if '1tv' in url.lower()]
                selected_url = tv1_urls[0] if tv1_urls else unique_urls[0]
            elif "2TV" in channel_name:
                tv2_urls = [url for url in unique_urls if '2tv' in url.lower()]
                selected_url = tv2_urls[0] if tv2_urls else unique_urls[0]
            else:
                selected_url = unique_urls[0]
            
            print(f"🔗 最终选择: {selected_url}")
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

def get_mbn_m3u8_enhanced(driver):
    """获取MBN的m3u8链接 - 专门优化MBN"""
    try:
        print("🚀 正在获取 MBN...")
        
        # 清除之前的网络日志
        driver.get_log('performance')
        
        driver.get("https://www.mbn.co.kr/vod/onair")
        
        # 更长的等待时间，确保页面和播放器脚本完全加载
        print("⏳ 等待MBN页面及播放器脚本完全加载...")
        time.sleep(25)  # 延长等待时间
        
        m3u8_urls = []
        target_domains = ['mbn.co.kr', 'hls-live.mbn.co.kr']
        
        # 方法1: 深度网络请求监控 (关键)
        print("🔍 深度监控MBN网络请求...")
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 如果没找到，尝试滚动页面触发加载
        if not m3u8_urls:
            print("🔄 首次未找到，滚动页面触发视频加载...")
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(8)
            network_urls = extract_m3u8_from_network_logs(driver, target_domains)
            m3u8_urls.extend(network_urls)

        # 如果仍未找到，尝试查找并点击播放按钮
        if not m3u8_urls:
            print("🔍 尝试查找并点击MBN播放按钮...")
            play_buttons = driver.find_elements(By.XPATH, "//button[contains(., '재생') or contains(., 'Play') or contains(., '보기') or contains(., '라이브')]")
            for button in play_buttons[:2]:
                try:
                    driver.execute_script("arguments[0].click();", button)
                    print("🖱️ 点击播放按钮")
                    time.sleep(8)
                    new_urls = extract_m3u8_from_network_logs(driver, target_domains)
                    m3u8_urls.extend(new_urls)
                    break
                except Exception as e:
                    print(f"点击按钮失败: {e}")
                    continue
        
        # 方法2: 深度搜索MBN页面源代码
        print("🔍 深度搜索MBN页面源代码...")
        page_source = driver.page_source
        
        m3u8_patterns = [
            r'https?://[^\s"\']*\.m3u8(?:\?[^\s"\']*)?',  # 匹配m3u8，可能带参数
            r'["\'](https?://[^"\']*\.m3u8[^"\']*)["\']', # 引号内的m3u8链接
            r'streamUrl\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', # streamUrl: 格式
            r'videoUrl\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'   # videoUrl: 格式
        ]
        
        for pattern in m3u8_patterns:
            source_urls = re.findall(pattern, page_source)
            mbn_urls = [url for url in source_urls if any(domain in url for domain in target_domains)]
            m3u8_urls.extend(mbn_urls)
            for url in mbn_urls:
                print(f"📄 从页面源码找到: {url}")
        
        # 方法3: MBN特定的播放器查找
        print("🔍 查找MBN特定播放器元素...")
        
        # MBN可能使用的播放器选择器
        player_selectors = [
            'video',
            'source',
            '[class*="video"]',
            '[class*="player"]',
            '[id*="video"]',
            '[id*="player"]',
            '.vod-player',
            '.mbn-player',
            '.live-player'
        ]
        
        for selector in player_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    # 检查src属性
                    src = element.get_attribute('src')
                    if src and '.m3u8' in src and any(domain in src for domain in target_domains):
                        m3u8_urls.append(src)
                        print(f"🎥 从{selector}找到: {src}")
                    
                    # 检查data-src等其他属性
                    for attr in ['data-src', 'data-url', 'data-video', 'data-stream']:
                        data_src = element.get_attribute(attr)
                        if data_src and '.m3u8' in data_src and any(domain in data_src for domain in target_domains):
                            m3u8_urls.append(data_src)
                            print(f"🎥 从{selector}[{attr}]找到: {data_src}")
            except Exception as e:
                continue
        
        # 方法4: 执行MBN特定的JavaScript (关键)
        print("🔍 执行MBN特定JavaScript...")
        mbn_scripts = [
            "Array.from(document.querySelectorAll('*')).filter(el => el.innerHTML && el.innerHTML.includes('.m3u8') && el.innerHTML.includes('mbn')).map(el => el.innerHTML.match(/(https?:\\/\\/[^\\s'\"]*\\.m3u8[^\\s'\"]*)/g)).filter(m => m).flat()",
            "window.videoPlayer && window.videoPlayer.getSource && window.videoPlayer.getSource()",
            "document.querySelector('[data-video-source]') && document.querySelector('[data-video-source]').getAttribute('data-video-source')",
            # 新增：尝试查找包含m3u8的JavaScript变量
            "JSON.stringify(Object.values(window).filter(val => typeof val === 'string' && val.includes('.m3u8') && val.includes('mbn')))"
        ]
        
        for script in mbn_scripts:
            try:
                result = driver.execute_script(f"return {script}")
                if result:
                    if isinstance(result, list):
                        valid_urls = [url for url in result if any(domain in url for domain in target_domains)]
                        m3u8_urls.extend(valid_urls)
                        if valid_urls:
                            print(f"💻 从JS执行找到: {valid_urls}")
                    elif isinstance(result, str) and '.m3u8' in result:
                        # 处理可能是JSON字符串的情况
                        if result.startswith('['):
                            try:
                                url_list = json.loads(result)
                                if isinstance(url_list, list):
                                    valid_urls = [url for url in url_list if any(domain in url for domain in target_domains)]
                                    m3u8_urls.extend(valid_urls)
                        else:
                            m3u8_urls.append(result)
            except Exception as e:
                print(f"执行脚本 {script} 时出错: {e}")
                continue
        
        # 去重并选择
        unique_urls = list(set(m3u8_urls))
        
        if unique_urls:
            print(f"📊 找到 {len(unique_urls)} 个MBN m3u8链接")
            
            # 智能选择MBN最佳URL
            # 优先选择包含chunklist和认证参数的URL (根据你手动抓取的特征)
            chunklist_auth_urls = [url for url in unique_urls if 'chunklist' in url and '?' in url and any(param in url for param in ['Policy=', 'Signature='])]
            if chunklist_auth_urls:
                selected_url = chunklist_auth_urls[0]
                print("✅ 找到 MBN chunklist认证地址")
            # 其次选择包含playlist的URL
            elif any('playlist' in url for url in unique_urls):
                playlist_urls = [url for url in unique_urls if 'playlist' in url]
                selected_url = playlist_urls[0]
            # 再次选择包含认证参数的URL
            elif any('?' in url and any(param in url for param in ['Policy=', 'Signature=']) for url in unique_urls):
                auth_urls = [url for url in unique_urls if '?' in url and any(param in url for param in ['Policy=', 'Signature='])]
                selected_url = auth_urls[0]
            else:
                selected_url = unique_urls[0]
            
            print(f"✅ 找到 MBN 真实m3u8地址: {selected_url}")
            return selected_url
        else:
            print("❌ 未找到 MBN 的真实m3u8地址，使用备用地址")
            # 返回你提供的备用地址
            return "https://hls-live.mbn.co.kr/mbn-on-air/600k/chunklist.m3u8"
            
    except Exception as e:
        print(f"❌ 获取 MBN 时出错: {str(e)}")
        # 返回你提供的备用地址
        return "https://hls-live.mbn.co.kr/mbn-on-air/600k/chunklist.m3u8"

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
        
        # 获取KBS 1TV - 使用增强版
        kbs1_url = get_kbs_m3u8_enhanced(driver, CHANNELS[0]['url'], CHANNELS[0]['name'])
        dynamic_channels.append({
            'name': CHANNELS[0]['name'],
            'tvg_id': CHANNELS[0]['tvg_id'],
            'url': kbs1_url
        })
        
        # 获取KBS 2TV - 使用增强版
        kbs2_url = get_kbs_m3u8_enhanced(driver, CHANNELS[1]['url'], CHANNELS[1]['name'])
        dynamic_channels.append({
            'name': CHANNELS[1]['name'],
            'tvg_id': CHANNELS[1]['tvg_id'],
            'url': kbs2_url
        })
        
        # 获取MBN - 使用增强版
        mbn_url = get_mbn_m3u8_enhanced(driver)
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
