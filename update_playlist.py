#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新Gist和固定仓库
修复版：优化KBS和MBC的直播源获取
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

# 配置信息
GITHUB_USERNAME = "GoonhoLee"
STABLE_REPO_NAME = "korean-tv-static"
GIST_ID = "1eefb097a9b3ec25c79bbd4149066d41"
FULL_ACCESS_TOKEN = os.getenv('FULL_ACCESS_TOKEN')
GITHUB_TOKEN = FULL_ACCESS_TOKEN

# 电视台配置
CHANNELS = [
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
    {
        "name": "MBN",
        "url": "https://www.mbn.co.kr/vod/onair",
        "tvg_id": "MBN.kr",
        "type": "mbn"
    },
    {
        "name": "MBC",
        "url": "https://onair.imbc.com/",
        "tvg_id": "MBC.kr", 
        "type": "mbc"
    }
]

# 静态频道列表（包含可靠的直播源）
STATIC_CHANNELS = [
    '#EXTINF:-1 tvg-id="KBS1TV.kr" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/KBS_1TV_2016_logo.svg/512px-KBS_1TV_2016_logo.svg.png" group-title="Korea",KBS 1TV (直播)',
    'https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8',
    '',
    '#EXTINF:-1 tvg-id="KBS2TV.kr" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/KBS_2TV_2016_logo.svg/512px-KBS_2TV_2016_logo.svg.png" group-title="Korea",KBS 2TV (直播)',
    'https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8',
    '',
    '#EXTINF:-1 tvg-id="MBC.kr" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/MBC_%EB%AC%B8%ED%99%94%EB%B0%A9%EC%86%A1.svg/512px-MBC_%EB%AC%B8%ED%99%94%EB%B0%A9%EC%86%A1.svg.png" group-title="Korea",MBC (直播)',
    'https://mvod.imbc.com/onair/1tv/onair.m3u8',
    '',
    '#EXTINF:-1 tvg-id="TVChosun.kr" tvg-logo="https://upload.wikimedia.org/wikipedia/ko/thumb/6/6a/TV_Chosun.svg/512px-TV_Chosun.svg.png" group-title="Korea",TV Chosun (720p)',
    '#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on.cstv',
    'http://onair.cdn.tvchosun.com/origin1/_definst_/tvchosun_s1/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="TVChosun2.kr" tvg-logo="https://upload.wikimedia.org/wikipedia/ko/thumb/6/6a/TV_Chosun.svg/512px-TV_Chosun.svg.png" group-title="Korea",TV Chosun 2 (720p)',
    '#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on2.cstv',
    'http://onair2.cdn.tvchosun.com/origin2/_definst_/tvchosun_s3/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="YTN.kr" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/YTN_logo.svg/512px-YTN_logo.svg.png" group-title="Korea",YTN',
    'https://ytnlive.ytn.co.kr/ytn/_definst_/ytnlive_stream_20220426/medialist_9171188557012390620_hls.m3u8',
    '',
    '#EXTINF:-1 tvg-id="EBS1TV.kr" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/EBS_1TV_Logo.svg/512px-EBS_1TV_Logo.svg.png" group-title="Korea",EBS 1 Ⓢ',
    'https://ebsonair.ebs.co.kr/ebs1familypc/familypc1m/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="EBS2TV.kr" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/EBS_2TV_Logo.svg/512px-EBS_2TV_Logo.svg.png" group-title="Korea",EBS 2 Ⓢ',
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
    
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_m3u8_from_logs(driver, target_domains, required_keywords=None):
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
                            # 域名过滤
                            if target_domains and not any(domain in url for domain in target_domains):
                                continue
                            # 关键词过滤
                            if required_keywords and not any(keyword in url.lower() for keyword in required_keywords):
                                continue
                            m3u8_urls.append(url)
            except Exception:
                continue
    except Exception as e:
        print(f"⚠️ 读取网络日志时出错: {e}")
    
    return list(set(m3u8_urls))

def get_kbs_m3u8(driver, url, channel_name):
    """获取KBS的直播m3u8链接"""
    try:
        print(f"🎬 正在获取 {channel_name} 直播源...")
        
        driver.get(url)
        time.sleep(15)  # 增加等待时间确保直播播放器加载
        
        target_domains = ['kbs.co.kr', 'gscdn.kbs.co.kr']
        required_keywords = ['1tv', '2tv', 'live']  # 直播相关关键词
        
        m3u8_urls = []
        
        # 网络请求监控 - 重点查找直播源
        network_urls = extract_m3u8_from_logs(driver, target_domains, required_keywords)
        m3u8_urls.extend(network_urls)
        
        # 如果没找到直播源，放宽条件再找一次
        if not m3u8_urls:
            print("🔍 未找到直播源，放宽条件重新搜索...")
            network_urls = extract_m3u8_from_logs(driver, target_domains, None)
            m3u8_urls.extend(network_urls)
        
        # 页面源代码搜索
        page_source = driver.page_source
        source_urls = re.findall(r'https?://[^\s"\']*\.m3u8[^\s"\']*', page_source)
        kbs_urls = [url for url in source_urls if any(domain in url for domain in target_domains)]
        m3u8_urls.extend(kbs_urls)
        
        # 智能选择直播URL
        unique_urls = list(set(m3u8_urls))
        
        if unique_urls:
            # 优先选择直播URL（包含1tv/2tv/live）
            live_urls = [url for url in unique_urls if any(keyword in url.lower() for keyword in required_keywords)]
            if live_urls:
                selected_url = live_urls[0]
                print(f"✅ 找到 {channel_name} 直播源: {selected_url[:80]}...")
                return selected_url
            else:
                # 其次选择带认证参数的URL
                auth_urls = [url for url in unique_urls if any(param in url for param in ['Expires=', 'Policy=', 'Signature='])]
                if auth_urls:
                    selected_url = auth_urls[0]
                    print(f"✅ 找到 {channel_name} 认证源: {selected_url[:80]}...")
                    return selected_url
                else:
                    selected_url = unique_urls[0]
                    print(f"⚠️ 找到 {channel_name} 源（可能非直播）: {selected_url[:80]}...")
                    return selected_url
        else:
            print(f"❌ 未找到 {channel_name} 直播源，使用静态直播地址")
            # 返回可靠的静态直播地址
            if "1TV" in channel_name:
                return "https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8"
            else:
                return "https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8"
                
    except Exception as e:
        print(f"❌ 获取 {channel_name} 时出错: {str(e)}")
        # 返回可靠的备用直播地址
        return "https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8" if "1TV" in channel_name else "https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8"

def get_mbc_m3u8(driver):
    """获取MBC的直播m3u8链接"""
    try:
        print("🎬 正在获取 MBC 直播源...")
        driver.get("https://onair.imbc.com/")
        time.sleep(15)  # 增加等待时间
        
        target_domains = ['imbc.com', 'mvod.imbc.com']
        required_keywords = ['onair', 'live', '1tv', 'broadcast']
        
        m3u8_urls = []
        
        # 深度网络监控
        print("🔍 深度监控MBC网络请求...")
        network_urls = extract_m3u8_from_logs(driver, target_domains, required_keywords)
        m3u8_urls.extend(network_urls)
        
        # 如果没找到，尝试点击可能的播放按钮
        if not m3u8_urls:
            print("🖱️ 尝试查找并点击播放按钮...")
            play_selectors = [
                "button[class*='play']",
                "a[class*='play']", 
                ".btn-play",
                ".play-button",
                "button:contains('재생')",
                "a:contains('재생')"
            ]
            
            for selector in play_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector.replace(":contains", ""))
                    for element in elements[:2]:
                        try:
                            if any(keyword in element.text.lower() for keyword in ['재생', 'play', '시청']):
                                print(f"🖱️ 点击播放按钮: {element.text}")
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(8)
                                # 点击后再次监控网络
                                new_urls = extract_m3u8_from_logs(driver, target_domains, required_keywords)
                                m3u8_urls.extend(new_urls)
                                break
                        except:
                            continue
                except:
                    continue
        
        # 页面源代码搜索
        page_source = driver.page_source
        source_urls = re.findall(r'https?://[^\s"\']*\.m3u8[^\s"\']*', page_source)
        mbc_urls = [url for url in source_urls if any(domain in url for domain in target_domains)]
        m3u8_urls.extend(mbc_urls)
        
        # 智能选择直播URL
        unique_urls = list(set(m3u8_urls))
        
        if unique_urls:
            # 优先选择直播URL
            live_urls = [url for url in unique_urls if any(keyword in url.lower() for keyword in required_keywords)]
            if live_urls:
                selected_url = live_urls[0]
                print(f"✅ 找到 MBC 直播源: {selected_url[:80]}...")
                return selected_url
            else:
                selected_url = unique_urls[0]
                print(f"⚠️ 找到 MBC 源（可能非直播）: {selected_url[:80]}...")
                return selected_url
        else:
            print("❌ 未找到MBC直播源，使用静态直播地址")
            return "https://mvod.imbc.com/onair/1tv/onair.m3u8"
            
    except Exception as e:
        print(f"❌ 获取 MBC 时出错: {str(e)}")
        return "https://mvod.imbc.com/onair/1tv/onair.m3u8"

def get_mbn_auth_url(auth_url):
    """从MBN认证链接获取真实m3u8地址"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.mbn.co.kr/vod/onair'
        }
        
        response = requests.get(auth_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            content = response.text.strip()
            if content.startswith('http') and '.m3u8' in content and 'hls-live.mbn.co.kr' in content:
                return content
        return None
    except Exception:
        return None

def get_mbn_m3u8(driver):
    """获取MBN的m3u8链接"""
    try:
        print("🎬 正在获取 MBN...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        time.sleep(12)
        
        target_domains = ['mbn.co.kr', 'hls-live.mbn.co.kr']
        m3u8_urls = extract_m3u8_from_logs(driver, target_domains)
        
        # 查找认证链接
        auth_urls = [url for url in m3u8_urls if 'mbnStreamAuth' in url]
        
        mbn_channels = []
        qualities = [
            {'quality': '1000k', 'name': 'MBN（高画质）'},
            {'quality': '600k', 'name': 'MBN（标清）'}
        ]
        
        for quality_info in qualities:
            quality = quality_info['quality']
            auth_url = next((url for url in auth_urls if quality in url), None)
            
            if auth_url:
                real_url = get_mbn_auth_url(auth_url)
                if real_url:
                    mbn_channels.append({
                        'name': quality_info['name'],
                        'tvg_id': 'MBN.kr',
                        'url': real_url,
                        'quality': quality
                    })
                    print(f"✅ 找到 {quality_info['name']}")
                    continue
            
            # 如果自动获取失败，使用备用地址
            backup_url = f"https://hls-live.mbn.co.kr/mbn-on-air/{quality}/playlist.m3u8"
            mbn_channels.append({
                'name': quality_info['name'],
                'tvg_id': 'MBN.kr',
                'url': backup_url,
                'quality': quality
            })
            print(f"⚠️ 使用备用地址: {quality_info['name']}")
        
        return mbn_channels
            
    except Exception as e:
        print(f"❌ 获取 MBN 时出错: {str(e)}")
        return [
            {
                'name': 'MBN（高画质）',
                'tvg_id': 'MBN.kr',
                'url': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8',
                'quality': '1000k'
            },
            {
                'name': 'MBN（标清）',
                'tvg_id': 'MBN.kr',
                'url': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8',
                'quality': '600k'
            }
        ]

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
        response = requests.get(url, headers=headers)
        sha = response.json().get('sha') if response.status_code == 200 else None
        
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
            static_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/main/korean_tv.m3u"
            print(f"🎉 固定仓库更新成功!")
            print(f"🔗 静态URL: {static_url}")
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
    lines.append("# 频道来源: KBS, MBC, MBN, TVChosun, YTN, EBS")
    lines.append("")
    
    # 添加动态获取的频道
    for channel in dynamic_channels:
        if channel.get('url'):
            lines.append(f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}" tvg-logo="" group-title="Korea",{channel["name"]}')
            lines.append(channel['url'])
            lines.append("")
    
    # 添加静态频道（确保直播源）
    lines.extend(STATIC_CHANNELS)
    
    return "\n".join(lines)

def main():
    """主函数"""
    print("🎬 开始获取韩国电视台直播源...")
    print("📡 目标频道: KBS 1TV, KBS 2TV, MBC, MBN")
    
    driver = None
    try:
        driver = setup_driver()
        dynamic_channels = []
        
        # 获取KBS频道
        for channel in [ch for ch in CHANNELS if ch['type'] == 'kbs']:
            url = get_kbs_m3u8(driver, channel['url'], channel['name'])
            dynamic_channels.append({
                'name': channel['name'],
                'tvg_id': channel['tvg_id'],
                'url': url
            })
        
        # 获取MBN频道（多画质）
        mbn_channels = get_mbn_m3u8(driver)
        dynamic_channels.extend(mbn_channels)
        
        # 获取MBC频道
        mbc_url = get_mbc_m3u8(driver)
        dynamic_channels.append({
            'name': 'MBC',
            'tvg_id': 'MBC.kr',
            'url': mbc_url
        })
        
        # 生成播放列表
        playlist_content = generate_playlist(dynamic_channels)
        print("✅ 播放列表生成完成!")
        
        # 更新到各个平台
        update_gist(playlist_content)
        update_stable_repository(playlist_content)
        
        # 保存本地文件
        with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
            f.write(playlist_content)
        print("💾 播放列表已保存到 korean_tv.m3u")
        
        # 打印统计信息
        successful_channels = [ch for ch in dynamic_channels if ch.get('url')]
        print(f"📊 成功获取 {len(successful_channels)} 个频道")
        
        # 显示频道详情
        print("\n📺 频道详情:")
        for channel in dynamic_channels:
            status = "✅" if channel.get('url') else "❌"
            print(f"  {status} {channel['name']}")
        
    except Exception as e:
        print(f"❌ 执行过程中出错: {str(e)}")
    finally:
        if driver:
            driver.quit()
            print("🔚 浏览器驱动已关闭")

if __name__ == "__main__":
    main()
