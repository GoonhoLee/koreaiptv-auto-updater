# update_playlist.py - 调试版本（跳过Gist更新）
import requests
import re
import os

def debug_fetch_kbs_live_url(ch_code, channel_name):
    """
    调试版本的KBS抓取函数
    """
    try:
        url = f"https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code={ch_code}&ch_type=globalList"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        print(f"🔍 开始抓取 {channel_name}...")
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   网页状态: {response.status_code}")
        
        # 搜索M3U8链接
        patterns = [
            r'https?://[^\s"\']*?\.m3u8[^\s"\']*',
            r'file\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
        ]
        
        found_links = []
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            print(f"   模式{i+1}找到 {len(matches)} 个匹配")
            
            for match in matches:
                clean_link = match.replace('\\/', '/')
                if '.m3u8' in clean_link:
                    found_links.append(clean_link)
                    print(f"     → 找到: {clean_link[:80]}...")
        
        print(f"   总共找到 {len(found_links)} 个M3U8链接")
        
        if found_links:
            # 优先选择包含kbs关键词的链接
            for link in found_links:
                if 'kbs' in link.lower():
                    print(f"   ✅ 选择含kbs关键词的链接")
                    return link
            print(f"   ⚠️ 使用首个找到的链接")
            return found_links[0]
        else:
            print(f"   ❌ 未找到M3U8链接")
            return None
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return None

def debug_fetch_mbn_live_url():
    """
    调试版本的MBN抓取函数
    """
    try:
        url = "https://www.mbn.co.kr/vod/onair"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        print(f"🔍 开始抓取 MBN...")
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   网页状态: {response.status_code}")
        
        patterns = [
            r'https?://[^\s"\']*?\.m3u8[^\s"\']*',
            r'file\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
        ]
        
        found_links = []
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            print(f"   模式{i+1}找到 {len(matches)} 个匹配")
            
            for match in matches:
                clean_link = match.replace('\\/', '/')
                if '.m3u8' in clean_link:
                    found_links.append(clean_link)
                    print(f"     → 找到: {clean_link[:80]}...")
        
        print(f"   总共找到 {len(found_links)} 个M3U8链接")
        
        if found_links:
            for link in found_links:
                if 'mbn' in link.lower():
                    print(f"   ✅ 选择含mbn关键词的链接")
                    return link
            print(f"   ⚠️ 使用首个找到的链接")
            return found_links[0]
        else:
            print(f"   ❌ 未找到M3U8链接")
            return None
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return None

def main():
    print("=" * 50)
    print("🎯 自动抓取功能测试")
    print("=" * 50)
    
    # 测试自动抓取
    print("\n📡 测试自动抓取功能:")
    
    kbs1_url = debug_fetch_kbs_live_url('11', 'KBS 1TV')
    kbs2_url = debug_fetch_kbs_live_url('12', 'KBS 2TV')
    mbn_url = debug_fetch_mbn_live_url()
    
    print(f"\n📊 抓取结果:")
    print(f"   KBS 1TV: {kbs1_url if kbs1_url else '抓取失败'}")
    print(f"   KBS 2TV: {kbs2_url if kbs2_url else '抓取失败'}")
    print(f"   MBN:     {mbn_url if mbn_url else '抓取失败'}")
    
    print(f"\n✅ 自动抓取测试完成！")
    print("💡 注意：此版本跳过了Gist更新，专注测试抓取功能")

if __name__ == "__main__":
    main()
