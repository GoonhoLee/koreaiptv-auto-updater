# update_playlist.py
import requests
import os
import re
import time
import json

# 配置信息
GIST_ID = "1eefb097a9b3ec25c79bbd4149066d41"
GH_TOKEN = os.environ.get('GH_PAT')
GIST_FILENAME = "korean_tv_playlist.m3u"

def check_gist_access():
    """检查Gist访问权限"""
    if not GH_TOKEN:
        print("❌ 错误: 未找到 GH_PAT 环境变量")
        return False
    
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
        if response.status_code == 200:
            gist_data = response.json()
            print(f"✅ Gist 访问成功")
            print(f"📝 Gist 描述: {gist_data.get('description', '无描述')}")
            print(f"👤 所有者: {gist_data['owner']['login']}")
            print(f"📁 文件: {list(gist_data['files'].keys())}")
            return True
        else:
            print(f"❌ Gist 访问失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 检查Gist时发生错误: {e}")
        return False

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
        
        # 去重
        found_links = list(set(found_links))
        
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
        
        # 去重
        found_links = list(set(found_links))
        
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
        'kbs1': 'https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8',
        'kbs2': 'https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8',
        'mbn': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/chunklist.m3u8'
    }

def update_gist(content):
    """更新Gist内容"""
    gist_url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "description": f"韩国电视频道自动更新列表 - 最后更新: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "files": {
            GIST_FILENAME: {
                "content": content
            }
        }
    }
    
    try:
        response = requests.patch(gist_url, headers=headers, json=data)
        if response.status_code == 200:
            gist_data = response.json()
            raw_url = gist_data['files'][GIST_FILENAME]['raw_url']
            print("🎉 Gist 更新成功!")
            print(f"🔗 原始文件地址: {raw_url}")
            return True
        else:
            print(f"❌ Gist 更新失败: {response.status_code}")
            print(f"错误详情: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 更新Gist时发生错误: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 韩国电视频道自动更新任务开始执行")
    print("=" * 60)
    
    # 0. 首先检查Gist访问权限
    print("\n🔐 阶段零: 检查Gist访问权限")
    if not check_gist_access():
        print("❌ 无法访问Gist，任务终止")
        return
    
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
    auto_status = {
        'kbs1': '成功' if kbs1_url != backup_links['kbs1'] else '备用',
        'kbs2': '成功' if kbs2_url != backup_links['kbs2'] else '备用', 
        'mbn': '成功' if mbn_url != backup_links['mbn'] else '备用'
    }
    
    m3u_content = f"""#EXTM3U x-tvg-url="https://raw.githubusercontent.com/linuxmuser/tv_data/master/tv_grab_kr_naver" refresh="3600"
# 韩国电视频道列表 - 自动更新版
# 项目地址: https://github.com/GoonhoLee/koreaiptv-auto-updater
# 更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
# 自动抓取状态: KBS1({auto_status['kbs1']}) | KBS2({auto_status['kbs2']}) | MBN({auto_status['mbn']})
# 此列表由 GitHub Actions 自动维护

# 主要频道 (自动更新)
#EXTINF:-1 tvg-id="KBS1.kr" tvg-name="KBS 1TV" tvg-logo="https://raw.githubusercontent.com/linuxmuser/tv_logos/main/kr/KBS1.png" group-title="지상파",KBS 1TV
{kbs1_url}

#EXTINF:-1 tvg-id="KBS2.kr" tvg-name="KBS 2TV" tvg-logo="https://raw.githubusercontent.com/linuxmuser/tv_logos/main/kr/KBS2.png" group-title="지상파",KBS 2TV
{kbs2_url}

#EXTINF:-1 tvg-id="MBN.kr" tvg-name="MBN" tvg-logo="https://raw.githubusercontent.com/linuxmuser/tv_logos/main/kr/MBN.png" group-title="종합편성",MBN
{mbn_url}

# 其他韩国频道 (固定链接)
#EXTINF:-1 tvg-id="TVChosun.kr" tvg-name="TV CHOSUN" tvg-logo="https://raw.githubusercontent.com/linuxmuser/tv_logos/main/kr/TVCHOSUN.png" group-title="종합편성",TV CHOSUN
http://onair.cdn.tvchosun.com/origin1/_definst_/tvchosun_s1/playlist.m3u8

#EXTINF:-1 tvg-id="YTN.kr" tvg-name="YTN" tvg-logo="https://raw.githubusercontent.com/linuxmuser/tv_logos/main/kr/YTN.png" group-title="보도",YTN
https://ytnlive.ytn.co.kr/ytn/_definst_/ytnlive_stream_20220426/medialist_9171188557012390620_hls.m3u8

#EXTINF:-1 tvg-id="EBS1.kr" tvg-name="EBS 1TV" tvg-logo="https://raw.githubusercontent.com/linuxmuser/tv_logos/main/kr/EBS1.png" group-title="교육",EBS 1TV
https://ebsonair.ebs.co.kr/ebs1familypc/familypc1m/playlist.m3u8

#EXTINF:-1 tvg-id="EBS2.kr" tvg-name="EBS 2TV" tvg-logo="https://raw.githubusercontent.com/linuxmuser/tv_logos/main/kr/EBS2.png" group-title="교육",EBS 2TV
https://ebsonair.ebs.co.kr/ebs2familypc/familypc1m/playlist.m3u8

#EXTINF:-1 tvg-id="KBSWorld.kr" tvg-name="KBS World" tvg-logo="https://raw.githubusercontent.com/linuxmuser/tv_logos/main/kr/KBSWORLD.png" group-title="해외",KBS World
https://kbsworld-ott.akamaized.net/hls/live/2002341/kbsworld/master.m3u8

#EXTINF:-1 tvg-id="KOREA.kr" tvg-name="Korea" tvg-logo="https://raw.githubusercontent.com/linuxmuser/tv_logos/main/kr/KOREA.png" group-title="해외",Korea
http://119.77.96.184:1935/chn21/chn21/playlist.m3u8

# 说明
#EXTINF:-1,=== 自动更新说明 ===
https://raw.githubusercontent.com/linuxmuser/tv_logos/main/.github/update_note.png

#EXTINF:-1,=== 项目地址 ===  
https://raw.githubusercontent.com/linuxmuser/tv_logos/main/.github/github.png"""
    
    # 5. 更新Gist
    print("\n📤 阶段四: 更新Gist")
    success = update_gist(m3u_content)
    
    if success:
        print("\n🎊 任务完成总结:")
        print(f"📺 KBS 1TV: {'🟢 自动抓取' if auto_status['kbs1'] == '成功' else '🟡 备用链接'}")
        print(f"📺 KBS 2TV: {'🟢 自动抓取' if auto_status['kbs2'] == '成功' else '🟡 备用链接'}")
        print(f"📺 MBN: {'🟢 自动抓取' if auto_status['mbn'] == '成功' else '🟡 备用链接'}")
        print(f"⏰ 更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("❌ 任务失败，请检查上述错误信息")

if __name__ == "__main__":
    main()
