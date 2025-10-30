#!/usr/bin/env python3
"""
自动抓取韩国电视台M3U8源并更新Gist
"""

import requests
import re
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

# Gist配置
GIST_ID = "1eefb097a9b3ec25c79bbd4149066d41"
GITHUB_TOKEN = "你的GitHub Token"  # 需要在GitHub Secrets中设置

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

# 静态频道列表（不需要动态抓取的）
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
    'https://ebsonair.ebs.co.kr/ebs2familypc/familypc1m/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-name="JTV TV" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Jtv_logo.svg/512px-Jtv_logo.svg.png" tvg-id="JTV.kr" group-title="Korea",JTV TV',
    'https://61ff3340258d2.streamlock.net/jtv_live/myStream/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-name="CJB TV" tvg-logo="https://i.imgur.com/MvxdZhX.png" tvg-id="CJBTV.kr" group-title="Korea",CJB TV',
    'http://1.222.207.80:1935/live/cjbtv/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-name="JIBS TV" tvg-logo="https://i.imgur.com/RVWpBoz.png" tvg-id="JIBSTV.kr" group-title="Korea",JIBS TV',
    'http://123.140.197.22/stream/1/play.m3u8',
    '',
    '#EXTINF:-1 tvg-id="KBSDrama.kr",KBS Drama (480p)',
    'http://mytv.dothome.co.kr/ch/catv/2.php',
    '',
    '#EXTINF:-1 tvg-id="TBSTV.kr",TBS Seoul (720p)',
    'https://cdntv.tbs.seoul.kr/tbs/tbs_tv_web.smil/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="ABN.kr",ABN TV (720p)',
    'https://vod2.abn.co.kr/IPHONE/abn.m3u8',
    '',
    '#EXTINF:-1 tvg-id="GoodTV.kr",GoodTV (1080p)',
    'http://mobliestream.c3tv.com:1935/live/goodtv.sdp/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="KBSJoy.kr",KBS Joy (480p)',
    'http://mytv.dothome.co.kr/ch/catv/3.php',
    '',
    '#EXTINF:-1 tvg-id="KBSLife.kr",KBS Life (480p)',
    'http://mytv.dothome.co.kr/ch/catv/5.php',
    '',
    '#EXTINF:-1 tvg-id="KBSStory.kr",KBS Story (480p)',
    'http://mytv.dothome.co.kr/ch/catv/4.php',
    '',
    '#EXTINF:-1 tvg-id="KBSWorld.kr",KBS World (720p)',
    'https://kbsworld-ott.akamaized.net/hls/live/2002341/kbsworld/master.m3u8',
    '',
    '#EXTINF:-1 tvg-id="",Korean Song Channel (720p)',
    'http://live.kytv.co.kr:8080/hls/stream.m3u8',
    '',
    '#EXTINF:-1 tvg-id="NHTV.kr",NHTV (720p)',
    'http://nonghyup.flive.skcdn.com/nonghyup/_definst_/nhlive/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="OUN.kr",OUN (1080p)',
    'https://live.knou.ac.kr/knou1/live1/playlist.m3u8',
    '',
    '#EXTINF:-1 tvg-id="EBS1.kr",EBS1 (1080p)',
    'http://ebsonairios.ebs.co.kr/groundwavetablet500k/tablet500k/chunklist.m3u8',
    '',
    '#EXTINF:-1 ,韩国KBC SBS综艺',
    'http://119.200.131.11:1935/KBCTV/tv/playlist.m3u8',
    '',
    '#EXTINF:-1 ,韩国KCTV',
    'http://119.77.96.184:1935/chn21/chn21/chunklist_w252131137.m3u8',
    '',
    '#EXTINF:-1 ,韩国MBC综艺频道',
    'http://vod.mpmbc.co.kr:1935/live/encoder-tv/playlist.m3u8',
    '',
    '#EXTINF:-1 ,韩国NBS农业广播',
    'https://media.joycorp.co.kr:4443/live/live_720p/playlist.m3u8',
    '',
    '#EXTINF:-1 ,韩国SBS CJB',
    'http://1.222.207.80:1935/live/cjbtv/chunklist_w1357270949.m3u8',
    '',
    '#EXTINF:-1 ,韩国TJB SBS综艺',
    'http://1.245.74.5:1935/live/tv/.m3u8',
    '',
    '#EXTINF:-1 ,韩国阿里郎WORLD',
    'http://amdlive.ctnd.com.edgesuite.net/arirang_1ch/smil:arirang_1ch/master.m3u8',
    '',
    '#EXTINF:-1 ,韩国电影2',
    'https://epg.pw/stream/3d0b0e644d73932ced9b2a9e4c4eb3371abdf1a867bbd27267e7650c2e25fe69.m3u8',
    '',
    '#EXTINF:-1 ,韩国电影3',
    'https://epg.pw/stream/8283baa9c305ecec457631b92ee1c01f25b4d6b8cf19e284d9efbd8de0789eb5.m3u8',
    '',
    '#EXTINF:-1 ,韩国中央',
    'http://119.77.96.184:1935/chn21/chn21/playlist.m3u8'
]

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_m3u8_from_network_logs(driver, wait_time=30):
    """从网络日志中提取m3u8链接"""
    try:
        # 获取性能日志
        logs = driver.get_log('performance')
        m3u8_urls = []
        
        for log in logs:
            try:
                message = json.loads(log['message'])
                message = message.get('message', {})
                
                if message.get('method') == 'Network.responseReceived':
                    url = message['params']['response']['url']
                    if '.m3u8' in url:
                        m3u8_urls.append(url)
            except:
                continue
        
        return list(set(m3u8_urls))  # 去重
    except:
        return []

def get_kbs_m3u8(driver, channel_url, channel_name):
    """获取KBS的m3u8链接"""
    try:
        print(f"正在获取 {channel_name}...")
        driver.get(channel_url)
        
        # 等待页面加载
        time.sleep(10)
        
        # 尝试查找视频元素
        m3u8_urls = []
        
        # 方法1: 查找video标签的src
        videos = driver.find_elements(By.TAG_NAME, 'video')
        for video in videos:
            src = video.get_attribute('src')
            if src and '.m3u8' in src:
                m3u8_urls.append(src)
        
        # 方法2: 从网络请求中查找
        network_urls = extract_m3u8_from_network_logs(driver)
        m3u8_urls.extend(network_urls)
        
        # 方法3: 在页面源代码中查找
        page_source = driver.page_source
        m3u8_pattern = r'https?://[^\s"\']*\.m3u8[^\s"\']*'
        source_urls = re.findall(m3u8_pattern, page_source)
        m3u8_urls.extend(source_urls)
        
        # 去重并返回第一个有效的m3u8链接
        unique_urls = list(set(m3u8_urls))
        for url in unique_urls:
            if url and ('kbs.co.kr' in url or 'kbs.co.kr' in url):
                print(f"找到 {channel_name} m3u8: {url}")
                return url
        
        print(f"未找到 {channel_name} 的m3u8链接")
        return None
        
    except Exception as e:
        print(f"获取 {channel_name} 时出错: {str(e)}")
        return None

def get_mbn_m3u8(driver):
    """获取MBN的m3u8链接"""
    try:
        print("正在获取 MBN...")
        driver.get("https://www.mbn.co.kr/vod/onair")
        
        # 等待页面加载
        time.sleep(10)
        
        m3u8_urls = []
        
        # 查找视频元素
        videos = driver.find_elements(By.TAG_NAME, 'video')
        for video in videos:
            src = video.get_attribute('src')
            if src and '.m3u8' in src:
                m3u8_urls.append(src)
        
        # 从网络请求中查找
        network_urls = extract_m3u8_from_network_logs(driver)
        m3u8_urls.extend(network_urls)
        
        # 在页面源代码中查找
        page_source = driver.page_source
        m3u8_pattern = r'https?://[^\s"\']*\.m3u8[^\s"\']*'
        source_urls = re.findall(m3u8_pattern, page_source)
        m3u8_urls.extend(source_urls)
        
        # 去重并返回MBN的m3u8链接
        unique_urls = list(set(m3u8_urls))
        for url in unique_urls:
            if url and 'mbn.co.kr' in url:
                print(f"找到 MBN m3u8: {url}")
                return url
        
        print("未找到 MBN 的m3u8链接")
        return None
        
    except Exception as e:
        print(f"获取 MBN 时出错: {str(e)}")
        return None

def update_gist(content):
    """更新Gist内容"""
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
    
    response = requests.patch(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        print("Gist更新成功!")
        return True
    else:
        print(f"Gist更新失败: {response.status_code} - {response.text}")
        return False

def generate_playlist(dynamic_channels):
    """生成完整的M3U播放列表"""
    lines = ["#EXTM3U"]
    lines.append(f"# 自动生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 添加动态获取的频道
    for channel in dynamic_channels:
        if channel['url']:
            lines.append(f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}",{channel["name"]}')
            lines.append(channel['url'])
            lines.append("")
    
    # 添加静态频道
    lines.extend(STATIC_CHANNELS)
    
    return "\n".join(lines)

def main():
    """主函数"""
    print("开始获取M3U8链接...")
    
    driver = None
    dynamic_channels = []
    
    try:
        driver = setup_driver()
        
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
        
        # 更新Gist
        if GITHUB_TOKEN != "你的GitHub Token":
            update_gist(playlist_content)
        else:
            # 如果没有设置token，则保存到本地文件
            with open('korean_tv.m3u', 'w', encoding='utf-8') as f:
                f.write(playlist_content)
            print("播放列表已保存到 korean_tv.m3u")
        
        print("任务完成!")
        
    except Exception as e:
        print(f"执行过程中出错: {str(e)}")
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
