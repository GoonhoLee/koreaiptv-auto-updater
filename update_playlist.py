#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新Gist
MBN完整修复版
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

def get_real_mbn_url_with_browser(driver, auth_url):
    """使用浏览器访问MBN认证链接获取真实m3u8地址"""
    try:
        print("🔗 使用浏览器访问MBN认证链接...")
        
        # 清除之前的网络日志
        driver.get_log('performance')
        
        # 访问认证链接
        driver.get(auth_url)
        time.sleep(8)  # 等待重定向完成
        
        # 监控重定向过程中的网络请求
        m3u8_urls = []
        target_domains = ['hls-live.mbn.co.kr']
        
        # 获取当前URL（可能是重定向后的地址）
        current_url = driver.current_url
        print(f"📍 当前URL: {current_url}")
        
        # 检查当前URL是否是真实的m3u8地址
        if 'hls-live.mbn.co.kr' in current_url and '.m3u8' in current_url:
            print(f"✅ 通过重定向获取到真实MBN地址: {current_url}")
            return current_url
        
        # 从网络请求中查找真实的m3u8地址
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 过滤出包含认证参数的URL
        real_urls = [url for url in m3u8_urls if '?' in url and 'Policy=' in url and 'Signature=' in url]
        
        if real_urls:
            selected_url = real_urls[0]
            print(f"✅ 从网络请求找到真实MBN地址: {selected_url}")
            return selected_url
        elif m3u8_urls:
            selected_url = m3u8_urls[0]
            print(f"⚠️ 找到MBN地址但可能缺少参数: {selected_url}")
            return selected_url
        else:
            print("❌ 未找到真实的MBN地址")
            return None
            
    except Exception as e:
        print(f"❌ 使用浏览器访问MBN认证链接时出错: {str(e)}")
        return None

def get_mbn_m3u8_enhanced(driver):
    """获取MBN的m3u8链接 - 增强版"""
    try:
        print("🚀 正在获取 MBN...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        time.sleep(20)
        
        m3u8_urls = []
        target_domains = ['mbn.co.kr', 'hls-live.mbn.co.kr']
        
        # 网络请求监控
        network_urls = extract_m3u8_from_network_logs(driver, target_domains)
        m3u8_urls.extend(network_urls)
        
        # 查找认证代理链接
        auth_urls = [url for url in m3u8_urls if 'mbnStreamAuth' in url]
        
        if auth_urls:
            print(f"🔍 找到MBN认证链接: {auth_urls[0]}")
            
            # 方法1: 使用浏览器访问认证链接获取真实地址
            real_url = get_real_mbn_url_with_browser(driver, auth_urls[0])
            if real_url:
                return real_url
            
            # 方法2: 如果浏览器方法失败，尝试直接请求认证链接
            print("🔄 尝试直接请求认证链接...")
            try:
                response = requests.get(auth_urls[0], timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    final_url = response.url
                    if 'hls-live.mbn.co.kr' in final_url and '.m3u8' in final_url:
                        print(f"✅ 通过重定向获取到MBN地址: {final_url}")
                        return final_url
                    
                    # 检查响应内容
                    content = response.text
                    if '.m3u8' in content:
                        m3u8_pattern = r'https?://[^\s"\']*\.m3u8[^\s"\']*'
                        urls = re.findall(m3u8_pattern, content)
                        real_urls = [url for url in urls if 'hls-live.mbn.co.kr' in url and '?' in url and 'Policy=' in url]
                        if real_urls:
                            print(f"✅ 从响应内容找到真实MBN地址: {real_urls[0]}")
                            return real_urls[0]
            except Exception as e:
                print(f"⚠️ 直接请求认证链接失败: {e}")
        
        # 方法3: 尝试从页面中提取JavaScript生成的URL
        print("🔍 尝试从页面提取MBN地址...")
        try:
            page_source = driver.page_source
            # 查找包含认证参数的m3u8 URL模式
            m3u8_patterns = [
                r'https?://hls-live\.mbn\.co\.kr/mbn-on-air/[^"\']*\.m3u8\?[^"\']*Policy=[^"\']*',
                r'["\'](https?://hls-live\.mbn\.co\.kr/[^"\']*\.m3u8\?[^"\']*Policy=[^"\']*)["\']'
            ]
            
            for pattern in m3u8_patterns:
                urls = re.findall(pattern, page_source)
                if urls:
                    print(f"✅ 从页面源码找到真实MBN地址: {urls[0]}")
                    return urls[0]
        except Exception as e:
            print(f"⚠️ 从页面提取失败: {e}")
        
        # 方法4: 执行JavaScript获取可能的URL
        print("🔍 尝试执行JavaScript获取MBN地址...")
        try:
            scripts = [
                "Array.from(document.querySelectorAll('script')).map(s => s.innerHTML).find(html => html.includes('hls-live.mbn.co.kr') && html.includes('.m3u8') && html.includes('Policy='))",
                "window.player && window.player.getConfig && window.player.getConfig().playlist && window.player.getConfig().playlist[0] && window.player.getConfig().playlist[0].file"
            ]
            
            for script in scripts:
                try:
                    result = driver.execute_script(f"return {script}")
                    if result and 'hls-live.mbn.co.kr' in result and '.m3u8' in result:
                        print(f"✅ 从JavaScript找到MBN地址: {result}")
                        return result
                except:
                    continue
        except Exception as e:
            print(f"⚠️ 执行JavaScript失败: {e}")
        
        print("❌ 所有方法都失败，使用备用地址")
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
