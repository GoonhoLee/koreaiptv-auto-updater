# update_korean_tv.py
import requests
import os

# 配置信息
GIST_ID = "9633c3cc086e124fe6d97c50f6321b39"  # 你的Gist ID
GH_TOKEN = os.environ['GH_PAT']  # 从GitHub Secrets读取令牌

def main():
    # 完整的韩国电视频道列表
    m3u_content = """#EXTM3U

# 韩国主要电视台
#EXTINF:-1 tvg-id="KBS1TV.kr",KBS 1TV
https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8?Expires=1761905893&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8xdHYuZ3NjZG4ua2JzLmNvLmtyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjE5MDU4OTN9fX1dfQ__&Signature=LfRdmyML5rjWGrAzcOHwyu~lyn2oSNPugRhLTP97fpCgpXEO51sBQjYu2eKIMvvjZtt23vOZE7lvES2zPHEztujgURhavKp96S3ZO5g1aHTARRDnY7JbJeP7ma1n9NR1c8N0EcwmISXeYPbD7AHwDXABNl62SUbvKLNvigV1AOpyq-b~IICmOOt4Y5EnqM9N~IE3wy1s-jWlgAkf5fbV0n-rcBkqgrGwAmIQj3VqCHncp4v5MXJhvJbhgqgTNJTBKfP6ASzns7JQhAGyjmYhdS1Jc3dRMM97rYrBDMEKXiBYR3wm18vENuaMvKf-uyTH5P1yCFpUatrcgHjLMBkOLA__&Key-Pair-Id=APKAICDSGT3Y7IXGJ3TA

#EXTINF:-1 tvg-id="KBS2TV.kr",KBS 2TV
https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8?Expires=1761905956&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8ydHYuZ3NjZG4ua2JzLmNvLmtyLyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjE5MDU5NTZ9fX1dfQ__&Signature=MGItWxRG8qGwHaG~UcgcqbSlOOB43OvnhIfMAkP-aXaCR8l96eo6WpRqrWkWSR~U5glIK1~bDiA0BQIAiXSgb2HVZp4M8brYDEHh4wZCzH0IVuPeN7Iqy5ib58heTmVMmt68CZ-yDbAdPK-mktdZWck7-gYrK8UiK3wvddvn6CbTEzfzB0S7~TG0vr47cPiygdeyrZaBqgI81ZeJ-Smk9u7YSUxIgHJt4GSSA72siQa-2zdkwD~5vjUTyoM01DwDZT7RY45G0tQXxDjQzY60JRoM3H~OhbsI7RCvYn6~5BSwteKtkAMzb-DdlAhrrirnzDJik-gPfGB2PyE38m50tw__&Key-Pair-Id=APKAICDSGT3Y7IXGJ3TA

#EXTINF:-1 tvg-id="TVChosun.kr",TV Chosun (720p)
#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on.cstv
http://onair.cdn.tvchosun.com/origin1/_definst_/tvchosun_s1/playlist.m3u8

#EXTINF:-1 tvg-id="TVChosun2.kr",TV Chosun 2 (720p)
#EXTVLCOPT:http-referrer=http://broadcast.tvchosun.com/onair/on2.cstv
http://onair2.cdn.tvchosun.com/origin2/_definst_/tvchosun_s3/playlist.m3u8

#EXTINF:-1 tvg-id="MBN.kr",MBN
https://hls-live.mbn.co.kr/mbn-on-air/600k/chunklist.m3u8?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cCo6Ly9obHMtbGl2ZS5tYm4uY28ua3IvKiIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2MTgxOTYwOH0sIklwQWRkcmVzcyI6eyJBV1M6U291cmNlSXAiOiIwLjAuMC4wLzAifX19XX0_&Signature=c9hliTbPDq56~RxC8KfQ0cvReQdteO~oejlxY6~9plml-0jDY6S9J30gfjHkg28aNUphcZy70KY8x0gH6wRAdtz1F2yO4kN6p-PgOhdDmVouSNo8jBxA-w9RRhkrcaXDqaPVYgyswHyHHEWc3RqlPu-ttgV~mkmhEYMfhDdeNv8_&Key-Pair-Id=pub_hls-live.mbn.co.kr

#EXTINF:-1 tvg-id="YTN.kr",YTN
https://ytnlive.ytn.co.kr/ytn/_definst_/ytnlive_stream_20220426/medialist_9171188557012390620_hls.m3u8

#EXTINF:-1 tvg-name="EBS 1 Ⓢ" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/EBS_1TV_Logo.svg/512px-EBS_1TV_Logo.svg.png" tvg-id="EBS1TV.kr" group-title="Korea",EBS 1 Ⓢ
https://ebsonair.ebs.co.kr/ebs1familypc/familypc1m/playlist.m3u8

#EXTINF:-1 tvg-name="EBS 2 Ⓢ" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/EBS_2TV_Logo.svg/512px-EBS_2TV_Logo.svg.png" tvg-id="EBS2TV.kr" group-title="Korea",EBS 2 Ⓢ
https://ebsonair.ebs.co.kr/ebs2familypc/familypc1m/playlist.m3u8

#EXTINF:-1 tvg-name="JTV TV" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Jtv_logo.svg/512px-Jtv_logo.svg.png" tvg-id="JTV.kr" group-title="Korea",JTV TV
https://61ff3340258d2.streamlock.net/jtv_live/myStream/playlist.m3u8

#EXTINF:-1 tvg-name="CJB TV" tvg-logo="https://i.imgur.com/MvxdZhX.png" tvg-id="CJBTV.kr" group-title="Korea",CJB TV
http://1.222.207.80:1935/live/cjbtv/playlist.m3u8

#EXTINF:-1 tvg-name="JIBS TV" tvg-logo="https://i.imgur.com/RVWpBoz.png" tvg-id="JIBSTV.kr" group-title="Korea",JIBS TV
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

#EXTINF:-1 ,韩国KBC SBS综艺
http://119.200.131.11:1935/KBCTV/tv/playlist.m3u8

#EXTINF:-1 ,韩国KCTV
http://119.77.96.184:1935/chn21/chn21/chunklist_w252131137.m3u8

#EXTINF:-1 ,韩国MBC综艺频道
http://vod.mpmbc.co.kr:1935/live/encoder-tv/playlist.m3u8

#EXTINF:-1 ,韩国NBS农业广播
https://media.joycorp.co.kr:4443/live/live_720p/playlist.m3u8

#EXTINF:-1 ,韩国SBS CJB
http://1.222.207.80:1935/live/cjbtv/chunklist_w1357270949.m3u8

#EXTINF:-1 ,韩国TJB SBS综艺
http://1.245.74.5:1935/live/tv/.m3u8

#EXTINF:-1 ,韩国阿里郎WORLD
http://amdlive.ctnd.com.edgesuite.net/arirang_1ch/smil:arirang_1ch/master.m3u8

#EXTINF:-1 ,韩国电影2
https://epg.pw/stream/3d0b0e644d73932ced9b2a9e4c4eb3371abdf1a867bbd27267e7650c2e25fe69.m3u8

#EXTINF:-1 ,韩国电影3
https://epg.pw/stream/8283baa9c305ecec457631b92ee1c01f25b4d6b8cf19e284d9efbd8de0789eb5.m3u8

#EXTINF:-1 ,韩国中央
http://119.77.96.184:1935/chn21/chn21/playlist.m3u8"""

    # 更新Gist
    gist_url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "files": {
            "zidong korean tv.m3u": {  # 你指定的M3U文件名
                "content": m3u_content
            }
        }
    }
    
    response = requests.patch(gist_url, headers=headers, json=data)
    if response.status_code == 200:
        print("✅ 韩国电视频道列表更新成功！")
        print("📺 包含30+个韩国频道")
    else:
        print(f"❌ 更新失败: {response.status_code}")
        print(f"错误信息: {response.text}")

if __name__ == "__main__":
    main()
