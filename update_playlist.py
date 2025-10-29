# update_playlist.py
import requests
import os
import re
import time

# 配置信息
GIST_ID = "1eefb097a9b3ec25c79bbd4149066d41"
GH_TOKEN = os.environ['GH_PAT']

def fetch_kbs_live_url(ch_code, channel_name):
    """
    从KBS官方页面抓取直播源链接
    """
    try:
        url = f"https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code={ch_code}&ch_type=globalList"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://onair.kbs.co.kr/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'
        }
        
        print(f"🎯 尝试自动抓取 {channel_name} 直播源...")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        # 多种匹配模式
        patterns = [
            r'https?://[^\s"\']*?\.m3u8[^\s"\']*',
            r'file\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
            r'src\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
            r'videoUrl\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
        ]
        
        found_links = []
        for pattern in patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            for match in matches:
                clean_link = match.replace('\\/', '/').replace('\\u002F', '/')
                if '.m3u8' in clean_link:
                    found_links.append(clean_link)
        
        # 优先选择包含频道关键词的链接
        for link in found_links:
            if f'kbs{ch_code}' in link.lower() or 'kbs' in link.lower():
                print(f"✅ 成功抓取 {channel_name}: {link[:80]}...")
                return link
        
        # 其次选择任何M3U8链接
        if found_links:
            print(f"⚠️  {channel_name} 使用通用M3U8链接: {found_links[0][:80]}...")
            return found_links[0]
        
        print(f"❌  {channel_name} 未找到M3U8链接")
        return None
        
    except Exception as e:
        print(f"❌ 抓取 {channel_name} 失败: {str(e)[:100]}")
        return None

def fetch_mbn_live_url():
    """
    从MBN官方页面抓取直播源链接
    """
    try:
        url = "https://www.mbn.co.kr/vod/onair"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.mbn.co.kr/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        print("🎯 尝试自动抓取 MBN 直播源...")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        patterns = [
            r'https?://[^\s"\']*?\.m3u8[^\s"\']*',
            r'file\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
            r'videoUrl\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
        ]
        
        found_links = []
        for pattern in patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            for match in matches:
                clean_link = match.replace('\\/', '/')
                if '.m3u8' in clean_link:
                    found_links.append(clean_link)
        
        # 优先选择包含mbn关键词的链接
        for link in found_links:
            if 'mbn' in link.lower():
                print(f"✅ 成功抓取 MBN: {link[:80]}...")
                return link
        
        if found_links:
            print(f"⚠️  MBN 使用通用M3U8链接: {found_links[0][:80]}...")
            return found_links[0]
        
        print("❌ MBN 未找到M3U8链接")
        return None
        
    except Exception as e:
        print(f"❌ 抓取 MBN 失败: {str(e)[:100]}")
        return None

def get_fallback_links():
    """
    备用链接 - 当自动抓取失败时使用
    """
    return {
        'kbs1': 'https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8?Expires=1761930315&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8xdHYuZ3NjZG4ua2JzLmNvLmtyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjE5MzAzMTV9fX1dfQ__&Signature=mhZQNn~G0ZV2rfbTt1xRqWVjoApulmuNyN8CL~VWUbQG6qwLRXbeuGsy3Rs4gDxeDtAPLsK2VLdrK~~TRKZndoY1zDUsgWtt~vqRFu8BN99D95sSYidWKxpLvmcHbBZgDdVjZx5Nah1edoIWUHX456rNAc5eXRLnxjZFzYkcf3-i8DDe4a0P2Fr1WtgtoCz1OnRHkiHmE0BnFam~bBej3ap55wnMdTo0S2seRSomIyUcs3oWOHgdS8JMneZDq2zS83zCUiRXKIyKwMax~0SCH42-H19uVo3tuGBPSrOh1XrZIBnG8NRf--eJogHdUauIZYdOGkvZer56gm4OBiRKzQ__&Key-Pair-Id=APKAICDSGT3Y7IXGJ3TA',
        'kbs2': 'https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8?Expires=1761905956&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8ydHYuZ3NjZG4ua2JzLmNvLmtyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjE5MDU5NTZ9fX1dfQ__&Signature=MGItWxRG8qGwHaG~UcgcqbSlOOB43OvnhIfMAkP-aXaCR8l96eo6WpRqrWkWSR~U5glIK1~bDiA0BQIAiXSgb2HVZp4M8brYDEHh4wZCzH0IVuPeN7Iqy5ib58heTmVMmt68CZ-yDbAdPK-mktdZWck7-gYrK8UiK3wvddvn6CbTEzfzB0S7~TG0vr47cPiygdeyrZaBqgI81ZeJ-Smk9u7YSUxIgHJt4GSSA72siQa-2zdkwD~5vjUTyoM01DwDZT7RY45G0tQXxDjQzY60JRoM3H~OhbsI7RCvYn6~5BSwteKtkAMzb-DdlAhrrirnzDJik-gPfGB2PyE38m50tw__&Key-Pair-Id=APKAICDSGT3Y7IXGJ3TA',
        'mbn': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/chunklist.m3u8'
    }

def main():
    print("=" * 50)
    print("🚀 开始执行自动抓取韩国电视频道任务")
    print("=" * 50)
    
    # 1. 尝试自动抓取最新链接
    print("\n📡 阶段一: 自动抓取直播源")
    kbs1_url = fetch_kbs_live_url('11', 'KBS 1TV')
    kbs2_url = fetch_kbs_live_url('12', 'KBS 2TV')
    mbn_url = fetch_mbn_live_url()
    
    # 2. 准备备用链接
    backup_links = get_fallback_links()
    
    # 3. 如果抓取失败，使用备用链接
    print("\n🛡️  阶段二: 备用方案检查")
    if not kbs1_url:
        print("⚠️  KBS 1TV 自动抓取失败，使用备用链接")
        kbs1_url = backup_links['kbs1']
    else:
        print("✅  KBS 1TV 使用自动抓取链接")
    
    if not kbs2_url:
        print("⚠️  KBS 2TV 自动抓取失败，使用备用链接")
        kbs2_url = backup_links['kbs2']
    else:
        print("✅  KBS 2TV 使用自动抓取链接")
    
    if not mbn_url:
        print("⚠️  MBN 自动抓取失败，使用备用链接")
        mbn_url = backup_links['mbn']
    else:
        print("✅  MBN 使用自动抓取链接")
    
    # 4. 构建完整的M3U播放列表
    print("\n📝 阶段三: 生成播放列表")
    m3u_content = f"""#EXTM3U
# 韩国电视频道列表 - 自动更新版
# 更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
# 自动抓取状态: KBS1({'成功' if kbs1_url != backup_links['kbs1'] else '备用'}) | KBS2({'成功' if kbs2_url != backup_links['kbs2'] else '备用'}) | MBN({'成功' if mbn_url != backup_links['mbn'] else '备用'})

# 主要频道 (自动更新)
#EXTINF:-1 tvg-id="KBS1TV.kr" tvg-name="KBS 1TV" group-title="韩国电视台",KBS 1TV
{kbs1_url}

#EXTINF:-1 tvg-id="KBS2TV.kr" tvg-name="KBS 2TV" group-title="韩国电视台",KBS 2TV
{kbs2_url}

#EXTINF:-1 tvg-id="MBN.kr" tvg-name="MBN" group-title="韩国电视台",MBN
{mbn_url}

# 其他韩国频道 (固定链接)
#EXTINF:-1 tvg-id="TVChosun.kr",TV Chosun
http://onair.cdn.tvchosun.com/origin1/_definst_/tvchosun_s1/playlist.m3u8

#EXTINF:-1 tvg-id="YTN.kr",YTN
https://ytnlive.ytn.co.kr/ytn/_definst_/ytnlive_stream_20220426/medialist_9171188557012390620_hls.m3u8

#EXTINF:-1 tvg-name="EBS 1 Ⓢ" tvg-id="EBS1TV.kr",EBS 1 Ⓢ
https://ebsonair.ebs.co.kr/ebs1familypc/familypc1m/playlist.m3u8

#EXTINF:-1 tvg-name="EBS 2 Ⓢ" tvg-id="EBS2TV.kr",EBS 2 Ⓢ
https://ebsonair.ebs.co.kr/ebs2familypc/familypc1m/playlist.m3u8

#EXTINF:-1 tvg-id="KBSWorld.kr",KBS World
https://kbsworld-ott.akamaized.net/hls/live/2002341/kbsworld/master.m3u8

#EXTINF:-1,韩国中央
http://119.77.96.184:1935/chn21/chn21/playlist.m3u8"""
    
    # 5. 更新Gist
    print("\n📤 阶段四: 更新Gist")
    gist_url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "files": {
            "TV.m3u": {
                "content": m3u_content
            }
        }
    }
    
    try:
        response = requests.patch(gist_url, headers=headers, json=data)
        if response.status_code == 200:
            print("🎉 任务完成! 播放列表更新成功!")
            print(f"📊 最终结果: KBS1({'🟢' if kbs1_url != backup_links['kbs1'] else '🟡'}) KBS2({'🟢' if kbs2_url != backup_links['kbs2'] else '🟡'}) MBN({'🟢' if mbn_url != backup_links['mbn'] else '🟡'})")
        else:
            print(f"❌ Gist更新失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 更新过程出错: {e}")

if __name__ == "__main__":
    main()
