# update_playlist.py
import requests
import re
import os
import time

# 配置信息（先不管Gist更新）
GIST_ID = "1eefb097a9b3ec25c79bbd4149066d41"
GH_TOKEN = os.environ['GH_PAT']

def debug_fetch_kbs_live_url(ch_code, channel_name):
    """
    调试版本的KBS抓取函数 - 详细输出抓取过程
    """
    try:
        url = f"https://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code={ch_code}&ch_type=globalList"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://onair.kbs.co.kr/'
        }
        
        print(f"\n🔍 开始抓取 {channel_name}...")
        print(f"   目标URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=20)
        print(f"   网页请求状态: {response.status_code}")
        
        # 保存网页内容用于分析（调试用）
        webpage_content = response.text
        print(f"   网页大小: {len(webpage_content)} 字符")
        
        # 显示网页前500个字符（看是否包含视频相关元素）
        preview = webpage_content[:500]
        print(f"   网页预览: {preview}...")
        
        # 多种匹配模式
        patterns = [
            r'https?://[^\s"\']*?\.m3u8[^\s"\']*',
            r'file\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
            r'src\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
            r'videoUrl\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
            r'streamUrl\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
        ]
        
        found_links = []
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, webpage_content, re.IGNORECASE)
            print(f"   模式{i+1}找到 {len(matches)} 个匹配")
            
            for match in matches:
                clean_link = match.replace('\\/', '/').replace('\\u002F', '/')
                if '.m3u8' in clean_link:
                    found_links.append(clean_link)
                    print(f"     → 找到M3U8: {clean_link[:80]}...")
        
        print(f"   总共找到 {len(found_links)} 个M3U8链接")
        
        # 分析找到的链接
        if found_links:
            print(f"   🔎 分析链接特征:")
            for i, link in enumerate(found_links):
                kbs_keyword = "有kbs关键词" if 'kbs' in link.lower() else "无kbs关键词"
                print(f"     {i+1}. {kbs_keyword}: {link[:60]}...")
            
            # 优先选择包含频道关键词的链接
            for link in found_links:
                if f'kbs{ch_code}' in link.lower() or 'kbs' in link.lower():
                    print(f"   ✅ 选择最佳链接（含kbs关键词）")
                    return link
            
            # 返回第一个找到的链接
            print(f"   ⚠️ 使用首个找到的链接")
            return found_links[0]
        else:
            print(f"   ❌ 未找到任何M3U8链接")
            return None
            
    except Exception as e:
        print(f"   ❌ 抓取过程出错: {e}")
        return None

def debug_fetch_mbn_live_url():
    """
    调试版本的MBN抓取函数
    """
    try:
        url = "https://www.mbn.co.kr/vod/onair"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.mbn.co.kr/'
        }
        
        print(f"\n🔍 开始抓取 MBN...")
        print(f"   目标URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=20)
        print(f"   网页请求状态: {response.status_code}")
        
        webpage_content = response.text
        print(f"   网页大小: {len(webpage_content)} 字符")
        
        # 显示网页前500个字符
        preview = webpage_content[:500]
        print(f"   网页预览: {preview}...")
        
        patterns = [
            r'https?://[^\s"\']*?\.m3u8[^\s"\']*',
            r'file\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
            r'videoUrl\s*:\s*["\'](https?://[^"\']*?\.m3u8[^"\']*?)["\']',
        ]
        
        found_links = []
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, webpage_content, re.IGNORECASE)
            print(f"   模式{i+1}找到 {len(matches)} 个匹配")
            
            for match in matches:
                clean_link = match.replace('\\/', '/')
                if '.m3u8' in clean_link:
                    found_links.append(clean_link)
                    print(f"     → 找到M3U8: {clean_link[:80]}...")
        
        print(f"   总共找到 {len(found_links)} 个M3U8链接")
        
        if found_links:
            print(f"   🔎 分析链接特征:")
            for i, link in enumerate(found_links):
                mbn_keyword = "有mbn关键词" if 'mbn' in link.lower() else "无mbn关键词"
                print(f"     {i+1}. {mbn_keyword}: {link[:60]}...")
            
            # 优先选择包含mbn关键词的链接
            for link in found_links:
                if 'mbn' in link.lower():
                    print(f"   ✅ 选择最佳链接（含mbn关键词）")
                    return link
            
            print(f"   ⚠️ 使用首个找到的链接")
            return found_links[0]
        else:
            print(f"   ❌ 未找到任何M3U8链接")
            return None
            
    except Exception as e:
        print(f"   ❌ 抓取过程出错: {e}")
        return None

def main():
    print("=" * 60)
    print("🔬 自动抓取功能调试测试")
    print("=" * 60)
    
    # 测试自动抓取功能
    print("\n🎯 阶段一：测试自动抓取功能")
    
    kbs1_url = debug_fetch_kbs_live_url('11', 'KBS 1TV')
    kbs2_url = debug_fetch_kbs_live_url('12', 'KBS 2TV') 
    mbn_url = debug_fetch_mbn_live_url()
    
    print(f"\n📊 抓取结果汇总:")
    print(f"   KBS 1TV: {'✅ ' + kbs1_url[:50] + '...' if kbs1_url else '❌ 抓取失败'}")
    print(f"   KBS 2TV: {'✅ ' + kbs2_url[:50] + '...' if kbs2_url else '❌ 抓取失败'}")
    print(f"   MBN:     {'✅ ' + mbn_url[:50] + '...' if mbn_url else '❌ 抓取失败'}")
    
    # 备用链接
    backup_links = {
        'kbs1': 'https://1tv.gscdn.kbs.co.kr/1tv_3.m3u8',
        'kbs2': 'https://2tv.gscdn.kbs.co.kr/2tv_1.m3u8',
        'mbn': 'https://hls-live.mbn.co.kr/mbn-on-air/600k/chunklist.m3u8'
    }
    
    # 应用备用链接
    final_kbs1 = kbs1_url or backup_links['kbs1']
    final_kbs2 = kbs2_url or backup_links['kbs2'] 
    final_mbn = mbn_url or backup_links['mbn']
    
    print(f"\n🎯 最终使用的链接:")
    print(f"   KBS 1TV: {final_kbs1[:80]}...")
    print(f"   KBS 2TV: {final_kbs2[:80]}...")
    print(f"   MBN:     {final_mbn[:80]}...")
    
    # 简化的Gist更新（避免404干扰测试）
    print(f"\n📤 跳过Gist更新，专注抓取功能测试")
    print("🎉 自动抓取功能测试完成！")

if __name__ == "__main__":
    main()
