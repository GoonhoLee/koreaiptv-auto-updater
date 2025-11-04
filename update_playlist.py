#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新Gist和固定仓库
修复KBS2版本，支持MBN多画质
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

# 电视台配置 - KBS DRAMA、KBS JOY、KBS STORY、KBS LIFE 放在最后面
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
    # 以下频道放在所有频道的最后面
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

# 静态频道列表 - 删除EBS1和EBS2
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

def generate_kbs_auth_url(base_url, expires_time=1762427233):
    """生成KBS认证m3u8 URL"""
    try:
        # 从基础URL提取信息
        if "1tv" in base_url:
            policy = "eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8xdHYuZ3NjZG4ua2JzLmNvLmtyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjI0MjcyMzN9fX1dfQ__"
            signature = "GBVxDBAnqoytflq9N1p5-qB0B8rGgiEpIjbXpi-Qc-L0g6MpVM13iQxNYC1v6aaDFJdFV2uAr9NC47IEMUibPkiBWSmhbcbxkN2SZOb0O6A9Cx0klgGw6GjdYcGq5pi3f3lqF-j4~VMKvlnFhLCWWWHvX~1sOwXlE4s7q-Wnt0u7H7LpaTI2cKPE~Vu7icLPd9Ayo9o2NZASPSkcx-uJN4WkWqip5kM8O093H5SNUPeqIw8b4yo7G8Yq2HpyW-vIwypyIlqdUUPSCrKsiyeqg2kh0hCJ2SZLXstGVRM8p4duw~mCXsJ1rVeD1CGFwulXa~~flfTvbx43MzF-4aT~bw__"
        elif "2tv" in base_url:
            policy = "eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8ydHYuZ3NjZG4ua2JzLmNvLmtyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjI0MjcyNzZ9fX1dfQ__"
            signature = "DgbgcW5Haz-YVw5bqq47O4HiEJvTBfwRUfkGetKgES3uhz506oZXUta9Kqg6qLy76ebdCm3gCYeMD9VoELebw~VceIckPB63j-Tty717Apj-M34J5KiebJCh1JkNiR04tY3YH48R~-AMT28a4Gx-GxfHVCIgcoWlqKL80-gIbevOWHpUCHZyqDnXs3omLSYai7lcV0MrQ3hG9bbG1jQyzkoMdv4lwMbeaBUcCuBLiUUjVcgR71-fQf8pGeNLlvUo0sskdATdAGp8t~tgxycTEBAelQEv2lCKLb341vc6cvh9QIEELGX4wR5pxSSQL~TkERoxj~DB5ExxWMM2shXfWw__"
        else:
            return base_url  # 如果不是KBS1或KBS2，返回原URL
        
        key_pair_id = "APKAICDSGT3Y7IXGJ3TA"
        
        # 生成认证URL
        auth_url = f"{base_url}?Expires={expires_time}&Policy={policy}&Signature={signature}&Key-Pair-Id={key_pair_id}"
        return auth_url
        
    except Exception as e:
        print(f"❌ 生成KBS认证URL时出错: {str(e)}")
        return base_url

def get_kbs_m3u8(driver, url, channel_name):
    """获取KBS的m3u8链接 - 修复KBS2版本"""
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
            else:
                selected_url = unique_urls[0]
                # 如果是KBS1或KBS2但没有认证参数，手动生成认证URL
                if "KBS1" in channel_name or "KBS2" in channel_name:
                    base_url = selected_url.split('?')[0]  # 获取基础URL
                    selected_url = generate_kbs_auth_url(base_url)
                    print(f"✅ 为 {channel_name} 生成认证地址")
            
            print(f"🔗 最终选择: {selected_url}")
            return selected_url
        else:
            print(f"❌ 未找到 {channel_name} 的真实m3u8地址，使用静态地址")
            # 返回静态地址
            if "KBS1" in channel_name:
                base_url = "https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8"
                return generate_kbs_auth_url(base_url)
            elif "KBS2" in channel_name:
                base_url = "https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8"
                return generate_kbs_auth_url(base_url)
            elif "24" in channel_name:
                return "https://news24.gscdn.kbs.co.kr/news24-02/news24-02_hd.m3u8"
            elif "DRAMA" in channel_name:
                return "https://kbsndrama.gscdn.kbs.co.kr/kbsndrama-02/kbsndrama-02_sd.m3u8"
            elif "JOY" in channel_name:
                return "https://kbsnjoy.gscdn.kbs.co.kr/kbsnjoy-02/kbsnjoy-02_sd.m3u8"
            elif "STORY" in channel_name:
                return "https://kbsnw.gscdn.kbs.co.kr/kbsnw-02/kbsnw-02_sd.m3u8"
            elif "LIFE" in channel_name:
                return "https://kbsnlife.gscdn.kbs.co.kr/kbsnlife-02/kbsnlife-02_sd.m3u8"
            return None
            
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

def get_mbn_m3u8_multiple_quality(driver):
    """获取MBN的m3u8链接 - 同时获取1000k和600k版本"""
    mbn_channels = []
    
    try:
        print("🚀 正在获取 MBN 多画质版本...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        time.sleep(15)
        
        m3u8_urls = []
        target_domains = ['mbn.co.kr', 'hls-live.mbn.co.kr']
        
        # 网络请求监控 - 查找认证链接
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 查找所有认证代理链接
        auth_urls = [url for url in m3u8_urls if 'mbnStreamAuth' in url]
        
        # 分别处理1000k和600k版本
        quality_configs = [
            {
                'quality': '1000k',
                'name': 'MBN（高画质）',
                'tvg_id': 'MBN.kr',
                'auth_urls': [url for url in auth_urls if '1000k' in url],
                'base_url': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8',
                'backup_url': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8'
            },
            {
                'quality': '600k',
                'name': 'MBN（标清）',
                'tvg_id': 'MBN.kr',
                'auth_urls': [url for url in auth_urls if '600k' in url],
                'base_url': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8',
                'backup_url': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8'
            }
        ]
        
        for config in quality_configs:
            print(f"\n🎯 正在获取 {config['quality']} 版本...")
            
            real_url = None
            
            # 首先尝试自动发现的认证链接
            if config['auth_urls']:
                print(f"🔍 找到 {config['quality']} 认证链接: {config['auth_urls'][0]}")
                real_url = get_real_mbn_url_from_response(config['auth_urls'][0])
                if real_url:
                    print(f"✅ 成功获取 {config['quality']} 版本")
                else:
                    print(f"❌ 自动发现的 {config['quality']} 认证链接无效")
            
            # 如果自动发现的链接失败，尝试构造认证链接
            if not real_url:
                print(f"🔄 尝试构造 {config['quality']} 认证链接...")
                constructed_auth_url = f"https://www.mbn.co.kr/player/mbnStreamAuth_new_live.mbn?vod_url={config['base_url']}"
                
                print(f"🔧 尝试构造的认证链接: {constructed_auth_url}")
                real_url = get_real_mbn_url_from_response(constructed_auth_url)
                if real_url:
                    print(f"✅ 通过构造链接获取 {config['quality']} 版本")
                else:
                    print(f"❌ 构造链接也失败，使用备用地址")
                    real_url = config['backup_url']
            
            # 添加到频道列表
            if real_url:
                mbn_channels.append({
                    'name': config['name'],
                    'tvg_id': config['tvg_id'],
                    'url': real_url,
                    'quality': config['quality']
                })
        
        # 如果两个版本都获取成功
        if len(mbn_channels) == 2:
            print("🎉 成功获取MBN双画质版本！")
        elif len(mbn_channels) == 1:
            print(f"⚠️ 只成功获取 {mbn_channels[0]['quality']} 版本")
        else:
            print("❌ 未能获取任何MBN版本，使用备用地址")
            # 添加备用地址
            mbn_channels.append({
                'name': 'MBN（高画质）',
                'tvg_id': 'MBN.kr',
                'url': 'https://hls-live.mbn.co.kr/mbn-on-air/1000k/playlist.m3u8',
                'quality': '1000k'
            })
            mbn_channels.append({
                'name': 'MBN（标清）',
                'tvg_id': 'MBN.kr',
                'url': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/playlist.m3u8',
                'quality': '600k'
            })
            
        return mbn_channels
            
    except Exception as e:
        print(f"❌ 获取 MBN 多画质版本时出错: {str(e)}")
        # 返回备用地址
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
        
    # 获取文件当前SHA（需要这个来更新文件）
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/contents/korean_tv.m3u"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # 首先尝试获取文件当前信息
        response = requests.get(url, headers=headers)
        sha = None
        if response.status_code == 200:
            sha = response.json().get('sha')
            print("📁 找到现有文件，准备更新...")
        else:
            print("📁 未找到现有文件，将创建新文件...")
        
        # 正确的Base64编码
        import base64
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('ascii')
        
        # 更新或创建文件
        data = {
            "message": f"自动更新播放列表 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_base64,  # 使用正确的Base64编码
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
            
            # 打印静态URL
            static_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{STABLE_REPO_NAME}/main/korean_tv.m3u"
            print(f"🔗 您的静态URL是: {static_url}")
            print("💡 请在Kodi中使用这个URL，它将自动更新!")
            return True
        else:
            print(f"❌ 固定仓库更新失败: {response.status_code} - {response.text}")
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
    print("🎬 开始获取M3U8链接...")
    print(f"📺 计划获取 {len(CHANNELS)} 个频道")
    
    driver = None
    try:
        driver = setup_driver()
        dynamic_channels = []
        
        # 遍历所有频道进行抓取
        for channel in CHANNELS:
            if "MBN" in channel['name']:
                # MBN特殊处理 - 多画质版本
                mbn_channels = get_mbn_m3u8_multiple_quality(driver)
                dynamic_channels.extend(mbn_channels)
                print(f"✅ {channel['name']} - 获取成功（双画质）")
            else:
                # KBS频道统一处理
                m3u8_url = get_kbs_m3u8(driver, channel['url'], channel['name'])
                if m3u8_url:
                    dynamic_channels.append({
                        'name': channel['name'],
                        'tvg_id': channel['tvg_id'],
                        'url': m3u8_url
                    })
                    print(f"✅ {channel['name']} - 获取成功")
                else:
                    print(f"❌ {channel['name']} - 获取失败")
        
        # 生成播放列表
        playlist_content = generate_playlist(dynamic_channels)
        print("✅ 播放列表生成完成!")
        
        # 更新Gist
        update_gist(playlist_content)
        
        # 更新固定仓库
        update_stable_repository(playlist_content)
        
        # 保存到本地文件
        with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
            f.write(playlist_content)
        print("💾 播放列表已保存到 korean_tv.m3u")
        
        # 打印统计
        successful_channels = [ch for ch in dynamic_channels if ch.get('url')]
        print(f"📊 成功获取 {len(successful_channels)}/{len(dynamic_channels)} 个频道")
        
        # 显示频道信息
        print("\n🎯 成功频道列表:")
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
