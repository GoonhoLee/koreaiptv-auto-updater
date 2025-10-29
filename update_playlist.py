# update_playlist.py
import requests
import os

# 配置信息
GIST_ID = "9633c3cc086e124fe6d97c50f6321b39"
GH_TOKEN = os.environ['GH_PAT']

def main():
    m3u_content = """#EXTM3U

#EXTINF:-1 tvg-id="KBS1TV.kr",KBS 1TV
https://kbsworld-ott.akamaized.net/hls/live/2021158/kbsworld/index.m3u8

#EXTINF:-1 tvg-id="KBS2TV.kr",KBS 2TV
https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8

#EXTINF:-1 tvg-id="TVChosun.kr",TV Chosun (720p)
http://onair.cdn.tvchosun.com/origin1/_definst_/tvchosun_s1/playlist.m3u8

#EXTINF:-1 tvg-id="MBN.kr",MBN
https://hls-live.mbn.co.kr/mbn-on-air/600k/chunklist.m3u8

#EXTINF:-1 tvg-id="YTN.kr",YTN
https://ytnlive.ytn.co.kr/ytn/_definst_/ytnlive_stream_20220426/medialist_9171188557012390620_hls.m3u8

# 这里是你所有的韩国频道...（为测试先放5个频道）"""

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
    
    response = requests.patch(gist_url, headers=headers, json=data)
    if response.status_code == 200:
        print("✅ 韩国电视频道列表更新成功！")
    else:
        print(f"❌ 更新失败: {response.status_code}")

if __name__ == "__main__":
    main()
