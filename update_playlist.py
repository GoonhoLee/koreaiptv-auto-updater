# update_playlist.py
import requests
import os
import re

# 配置信息
GIST_ID = "1eefb097a9b3ec25c79bbd4149066d41"  # 新的Gist ID
GH_TOKEN = os.environ['GH_PAT']  # 从GitHub Secrets读取令牌

def fetch_kbs_live_url(ch_code):
    """
    从KBS官方页面抓取指定频道的直播源(m3u8)链接。
    """
    try:
        url = f"https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code={ch_code}&ch_type=globalList"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://onair.kbs.co.kr/'
        }
        
        print(f"🕐 正在从KBS官网获取频道代码 {ch_code} 的直播链接...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 多种匹配模式尝试寻找M3U8链接
        m3u8_patterns = [
            r'https?://[^\s"\']*?\.m3u8[^\s"\']*',
            r'file\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
            r'src\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
        ]
        
        for pattern in m3u8_patterns:
            m3u8_matches = re.findall(pattern, response.text, re.IGNORECASE)
            if m3u8_matches:
                # 优先选择包含kbs关键词的链接
                for link in m3u8_matches:
                    clean_link = link.replace('\\/', '/')
                    if 'kbs' in clean_link.lower():
                        print(f"✅ 通过关键词找到KBS{ch_code}链接: {clean_link}")
                        return clean_link
                # 如果没有包含kbs的链接，返回第一个找到的
                first_link = m3u8_matches[0].replace('\\/', '/')
                print(f"⚠️ 使用找到的首个M3U8链接: {first_link}")
                return first_link
        
        print(f"❌ 未在KBS{ch_code}页面中找到M3U8链接")
        return None
        
    except Exception as e:
        print(f"❌ 获取KBS{ch_code}链接失败: {e}")
        return None

def fetch_mbn_live_url():
    """
    从MBN官方页面抓取直播源链接。
    """
    try:
        url = "https://www.mbn.co.kr/vod/onair"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.mbn.co.kr/'
        }
        
        print("🕐 正在从MBN官网获取直播链接...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 在MBN页面中寻找直播流链接
        m3u8_patterns = [
            r'https?://[^\s"\']*?\.m3u8[^\s"\']*',
            r'file\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
            r'videoUrl\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
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
        
    except Exception as e:
        print(f"❌ 获取MBN链接失败: {e}")
        return None

def get_fallback_links():
    """
    提供备用的直播链接。
    当无法从官网获取时使用此备用链接。
    """
    backup_links = {
        'kbs1': 'https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8?Expires=1761930315&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8xdHYuZ3NjZG4ua2JzLmNvLmtyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjE5MzAzMTV9fX1dfQ__&Signature=mhZQNn~G0ZV2rfbTt1xRqWVjoApulmuNyN8CL~VWUbQG6qwLRXbeuGsy3Rs4gDxeDtAPLsK2VLdrK~~TRKZndoY1zDUsgWtt~vqRFu8BN99D95sSYidWKxpLvmcHbBZgDdVjZx5Nah1edoIWUHX456rNAc5eXRLnxjZFzYkcf3-i8DDe4a0P2Fr1WtgtoCz1OnRHkiHmE0BnFam~bBej3ap55wnMdTo0S2seRSomIyUcs3oWOHgdS8JMneZDq2zS83zCUiRXKIyKwMax~0SCH42-H19uVo3tuGBPSrOh1XrZIBnG8NRf--eJogHdUauIZYdOGkvZer56gm4OBiRKzQ__&Key-Pair-Id=APKAICDSGT3Y7IXGJ3TA',
        'kbs2': 'https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8?Expires=1761905956&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8ydHYuZ3NjZG4ua2JzLmNvLmtyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjE5MDU5NTZ9fX1dfQ__&Signature=MGItWxRG8qGwHaG~UcgcqbSlOOB43OvnhIfMAkP-aXaCR8l96eo6WpRqrWkWSR~U5glIK1~bDiA0BQIAiXSgb2HVZp4M8brYDEHh4wZCzH0IVuPeN7Iqy5ib58heTmVMmt68CZ-yDbAdPK-mktdZWck7-gYrK8UiK3wvddvn6CbTEzfzB0S7~TG0vr47cPiygdeyrZaBqgI81ZeJ-Smk9u7YSUxIgHJt4GSSA72siQa-2zdkwD~5vjUTyoM01DwDZT7RY45G0tQXxDjQzY60JRoM3H~OhbsI7RCvYn6~5BSwteKtkAMzb-DdlAhrrirnzDJik-gPfGB2PyE38m50tw__&Key-Pair-Id=APKAICDSGT3Y7IXGJ3TA',
        'mbn': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/chunklist.m3u8?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cCo6Ly9obHMtbGl2ZS5tYm4uY28ua3IvKiIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2MTgxOTYwOH0sIklwQWRkcmVzcyI6eyJBV1M6U291cmNlSXAiOiIwLjAuMC4wLzAifX19XX0_&Signature=c9hliTbPDq56~RxC8KfQ0cvReQdteO~oejlxY6~9plml-0jDY6S9J30gfjHkg28aNUphcZy70KY8x0gH6wRAdtz1F2yO4kN6p-PgOhdDmVouSNo8jBxA-w9RRhkrcaXDqaPVYgyswHyHHEWc3RqlPu-ttgV~mkmhEYMfhDdeNv8_&Key-Pair-Id=pub_hls-live.mbn.co.kr'
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

#EXTINF:-1 tvg-id="TVChosun2.kr",TV Chosun 2 (720p)
#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on2.cstv
http://onair2.cdn.tvchosun.com/origin2/_definst_/tvchosun_s3/playlist.m3u8

#EXTINF:-1 tvg-id="YTN.kr",YTN
https://ytnlive.ytn.co.kr/ytn/_definst_/ytnlive_stream_20220426/medialist_9171188557012390620_hls.m3u8

#EXTINF:-1 tvg-name="EBS 1 Ⓢ" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/EBS_1TV_Logo.svg/512px-EBS_1TV_Logo.svg.png" tvg-id="EBS1TV.kr" group-title="韩国电视台",EBS 1 Ⓢ
https://ebsonair.ebs.co.kr/ebs1familypc/familypc1m/playlist.m3u8

#EXTINF:-1 tvg-name="EBS 2 Ⓢ" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/EBS_2TV_Logo.svg/512px-EBS_2TV_Logo.svg.png" tvg-id="EBS2TV.kr" group-title="韩国电视台",EBS 2 Ⓢ
https://ebsonair.ebs.co.kr/ebs2familypc/familypc1m/playlist.m3u8

#EXTINF:-1 tvg-name="JTV TV" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Jtv_logo.svg/512px-Jtv_logo.svg.png" tvg-id="JTV.kr" group-title="韩国电视台",JTV TV
https://61ff3340258d2.streamlock.net/jtv_live/myStream/playlist.m3u8

#EXTINF:-1 tvg-name="CJB TV" tvg-logo="https://i.imgur.com/MvxdZhX.png" tvg-id="CJBTV.kr" group-title="韩国电视台",CJB TV
http://1.222.207.80:1935/live/cjbtv/playlist.m3u8

#EXTINF:-1 tvg-name="JIBS TV" tvg-logo="https://i.imgur.com/RVWpBoz.png" tvg-id="JIBSTV.kr" group-title="韩国电视台",JIBS TV
http://123.140.197.22/stream/1/play.m3u8

#EXTINF:-1 tvg-id="KBSDrama.kr",KBS Drama (480p)
http://mytv.dothome.co.kr/ch/catv/2.php

#EXTINF:-1 tvg-id="TBSTV.kr",TBS Seoul (720p)
https://cdntv.tbs.seoul.kr/tbs/tbs_tv_web.smil/playlist.m3u8

#EXTINF:-1 tvg-id="ABN.kr",ABN TV (720p)
https://vod2.abn.co.kr/IPHONE/abn.m3u8

#EXTINF:-1 tvg-id="GoodTV.kr",GoodTV (1080p)
http://mobliestream.c3tv.com:1935/live/goodtv.sdp/playlist.m3u8

#EXTINF:-1 tvg-id="KBSJoy.kr",KBS Joy (480p)
http://mytv.dothome.co.kr/ch/catv/3.php

#EXTINF:-1 tvg-id="KBSLife.kr",KBS Life (480p)
http://mytv.dothome.co.kr/ch/catv/5.php

#EXTINF:-1 tvg-id="KBSStory.kr",KBS Story (480p)
http://mytv.dothome.co.kr/ch/catv/4.php

#EXTINF:-1 tvg-id="KBSWorld.kr",KBS World (720p)
https://kbsworld-ott.akamaized.net/hls/live/2002341/kbsworld/master.m3u8

#EXTINF:-1 tvg-id="",Korean Song Channel (720p)
http://live.kytv.co.kr:8080/hls/stream.m3u8

#EXTINF:-1 tvg-id="NHTV.kr",NHTV (720p)
http://nonghyup.flive.skcdn.com/nonghyup/_definst_/nhlive/playlist.m3u8

#EXTINF:-1 tvg-id="OUN.kr",OUN (1080p)
https://live.knou.ac.kr/knou1/live1/playlist.m3u8

#EXTINF:-1 tvg-id="EBS1.kr",EBS1 (1080p)
http://ebsonairios.ebs.co.kr/groundwavetablet500k/tablet500k/chunklist.m3u8

#EXTINF:-1,韩国KBC SBS综艺
http://119.200.131.11:1935/KBCTV/tv/playlist.m3u8

#EXTINF:-1,韩国KCTV
http://119.77.96.184:1935/chn21/chn21/chunklist_w252131137.m3u8

#EXTINF:-1,韩国MBC综艺频道
http://vod.mpmbc.co.kr:1935/live/encoder-tv/playlist.m3u8

#EXTINF:-1,韩国NBS农业广播
https://media.joycorp.co.kr:4443/live/live_720p/playlist.m3u8

#EXTINF:-1,韩国SBS CJB
http://1.222.207.80:1935/live/cjbtv/chunklist_w1357270949.m3u8

#EXTINF:-1,韩国TJB SBS综艺
http://1.245.74.5:1935/live/tv/.m3u8

#EXTINF:-1,韩国阿里郎WORLD
http://amdlive.ctnd.com.edgesuite.net/arirang_1ch/smil:arirang_1ch/master.m3u8

#EXTINF:-1,韩国电影2
https://epg.pw/stream/3d0b0e644d73932ced9b2a9e4c4eb3371abdf1a867bbd27267e7650c2e25fe69.m3u8

#EXTINF:-1,韩国电影3
https://epg.pw/stream/8283baa9c305ecec457631b92ee1c01f25b4d6b8cf19e284d9efbd8de0789eb5.m3u8

#EXTINF:-1,韩国中央
http://119.77.96.184:1935/chn21/chn21/playlist.m3u8"""

    # 5. 更新Gist
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
