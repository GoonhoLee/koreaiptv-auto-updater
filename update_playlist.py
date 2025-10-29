# update_playlist.py
import requests
import os
import re

# 配置信息
GIST_ID = "9633c3cc086e124fe6d97c50f6321b39"  # 请确保这是您存放播放列表的Gist ID
GH_TOKEN = os.environ['GH_PAT']  # 从GitHub Secrets读取令牌

def fetch_kbs_live_url(ch_code):
    """
    从KBS官方页面抓取指定频道的直播源(m3u8)链接。
    
    Args:
        ch_code: 频道代码，'11' 对应 KBS1, '12' 对应 KBS2

    Returns:
        成功返回m3u8链接字符串，失败返回None。
    """
    try:
        url = f"https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code={ch_code}&ch_type=globalList"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"🕐 正在从KBS官网获取频道代码 {ch_code} 的直播链接...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 调试：打印网页前1000个字符以便排查问题
        # print(f"网页内容预览: {response.text[:1000]}")
        
        # 改进的匹配模式，尝试寻找更准确的m3u8链接
        m3u8_patterns = [
            r'https?://[^\s"\']*?\.m3u8[^\s"\']*',  # 标准m3u8链接
            r'file\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',  # 匹配JS中的file: "..."格式
        ]
        
        for pattern in m3u8_patterns:
            m3u8_matches = re.findall(pattern, response.text, re.IGNORECASE)
            if m3u8_matches:
                # 优先选择包含kbs关键词的链接
                for link in m3u8_matches:
                    clean_link = link.replace('\\/', '/')  # 清理可能的转义斜杠
                    if 'kbs' in clean_link.lower():
                        print(f"✅ 通过关键词找到KBS{ch_code}链接: {clean_link}")
                        return clean_link
                # 如果没有包含kbs的链接，返回第一个找到的
                first_link = m3u8_matches[0].replace('\\/', '/')
                print(f"⚠️ 使用找到的首个M3U8链接: {first_link}")
                return first_link
        
        print(f"❌ 未在KBS{ch_code}页面中找到M3U8链接")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取KBS{ch_code}链接网络请求出错: {e}")
        return None
    except Exception as e:
        print(f"❌ 解析KBS{ch_code}页面过程出错: {e}")
        return None

def fetch_mbn_live_url():
    """
    从MBN官方页面抓取直播源链接。

    Returns:
        成功返回m3u8链接字符串，失败返回None。
    """
    try:
        url = "https://www.mbn.co.kr/vod/onair"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.mbn.co.kr/'
        }
        
        print("🕐 正在从MBN官网获取直播链接...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 在MBN页面中寻找直播流链接
        m3u8_patterns = [
            r'https?://[^\s"\']*?\.m3u8[^\s"\']*',
            r'file\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
            r'videoUrl\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',  # 匹配videoUrl格式
        ]
        
        for pattern in m3u8_patterns:
            m3u8_matches = re.findall(pattern, response.text, re.IGNORECASE)
            if m3u8_matches:
                # 优先选择包含mbn关键词的链接
                for link in m3u8_matches:
                    clean_link = link.replace('\\/', '/')
                    if 'mbn' in clean_link.lower():
                        print(f"✅ 通过关键词找到MBN链接: {clean_link}")
                        return clean_link
                # 返回第一个找到的链接
                first_link = m3u8_matches[0].replace('\\/', '/')
                print(f"⚠️ 使用找到的首个MBN M3U8链接: {first_link}")
                return first_link
        
        print("❌ 未在MBN页面中找到M3U8链接")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取MBN链接网络请求出错: {e}")
        return None
    except Exception as e:
        print(f"❌ 解析MBN页面过程出错: {e}")
        return None

def get_fallback_links():
    """
    提供备用的直播链接。
    当无法从官网获取时使用此备用链接。
    """
    backup_links = {
        'kbs1': 'https://kbsworld-ott.akamaized.net/hls/live/2021158/kbsworld/index.m3u8',
        'kbs2': 'https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8',  # 示例备用链接
        'mbn': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/chunklist.m3u8'  # 示例备用链接
    }
    return backup_links

def main():
    print("🚀 开始自动更新韩国电视频道列表...")
    
    # 1. 尝试从官网获取最新链接
    kbs1_url = fetch_kbs_live_url('11')  # KBS1频道代码为11
    kbs2_url = fetch_kbs_live_url('12')  # KBS2频道代码为12
    mbn_url = fetch_mbn_live_url()
    
    # 2. 获取备用链接字典
    backup_links = get_fallback_links()
    
    # 3. 如果获取失败，使用备用链接
    if not kbs1_url:
        print("⚠️ KBS1使用备用直播链接")
        kbs1_url = backup_links['kbs1']
    
    if not kbs2_url:
        print("⚠️ KBS2使用备用直播链接")
        kbs2_url = backup_links['kbs2']
    
    if not mbn_url:
        print("⚠️ MBN使用备用直播链接")
        mbn_url = backup_links['mbn']
    
    # 4. 构建完整的M3U播放列表内容
    m3u_content = f"""#EXTM3U
# 自动更新的韩国电视频道列表
# 来源: KBS官方页面 + MBN官方页面 + GitHub Actions自动化
# 更新时间: 自动维护

# KBS频道 (自动从官网获取)
#EXTINF:-1 tvg-id="KBS1TV.kr" tvg-name="KBS 1TV" tvg-logo="https://www.kbs.co.kr/img/ci/ci_01.png" group-title="韩国电视台",KBS 1TV (自动更新)
{kbs1_url}

#EXTINF:-1 tvg-id="KBS2TV.kr" tvg-name="KBS 2TV" tvg-logo="https://www.kbs.co.kr/img/ci/ci_02.png" group-title="韩国电视台",KBS 2TV (自动更新)
{kbs2_url}

# MBN频道 (自动从官网获取)
#EXTINF:-1 tvg-id="MBN.kr" tvg-name="MBN" tvg-logo="https://www.mbn.co.kr/favicon.ico" group-title="韩国电视台",MBN (自动更新)
{mbn_url}

# 其他韩国频道 (固定链接)
#EXTINF:-1 tvg-id="TVChosun.kr",TV Chosun (720p)
#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on.cstv
http://onair.cdn.tvchosun.com/origin1/_definst_/tvchosun_s1/playlist.m3u8

#EXTINF:-1 tvg-name="EBS 1 Ⓢ" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/EBS_1TV_Logo.svg/512px-EBS_1TV_Logo.svg.png" tvg-id="EBS1TV.kr" group-title="韩国电视台",EBS 1 Ⓢ
https://ebsonair.ebs.co.kr/ebs1familypc/familypc1m/playlist.m3u8

#EXTINF:-1 tvg-name="EBS 2 Ⓢ" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/EBS_2TV_Logo.svg/512px-EBS_2TV_Logo.svg.png" tvg-id="EBS2TV.kr" group-title="韩国电视台",EBS 2 Ⓢ
https://ebsonair.ebs.co.kr/ebs2familypc/familypc1m/playlist.m3u8

#EXTINF:-1 tvg-id="KBSWorld.kr",KBS World (720p)
https://kbsworld-ott.akamaized.net/hls/live/2002341/kbsworld/master.m3u8

# ... 这里可以继续添加您其他的韩国频道，格式保持不变 ...
"""
    # 注意：如果您有更多频道，请在上面的m3u_content变量中继续添加，保持相同的格式

    # 5. 更新Gist
    gist_url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "files": {
            "zidong korean tv.m3u": {
                "content": m3u_content
            }
        }
    }
    
    print("📡 正在更新Gist...")
    response = requests.patch(gist_url, headers=headers, json=data)
    
    if response.status_code == 200:
        print("✅ 韩国电视频道列表更新成功！")
        print(f"📺 KBS1链接: {kbs1_url}")
        print(f"📺 KBS2链接: {kbs2_url}")
        print(f"📺 MBN链接: {mbn_url}")
    else:
        print(f"❌ Gist更新失败: {response.status_code}")
        print(f"错误详情: {response.text}")

if __name__ == "__main__":
    main()
