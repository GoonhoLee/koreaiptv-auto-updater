# 🎬 韩国电视台直播源 M3U 播放列表

自动抓取韩国电视台直播源并生成 M3U 播放列表，支持 KBS、MBN、TV朝鲜、YTN 等多个频道。

## 📺 支持的频道列表

### 🎥 主要频道
- **KBS1** - KBS 1TV
- **KBS2** - KBS 2TV  
- **KBS 24** - KBS 24小时新闻
- **MBN** - 每日广播（提供高画质和标清双版本）
- **TV Chosun** - 朝鲜电视台
- **TV Chosun 2** - 朝鲜电视台2
- **YTN** - YTN新闻频道

### 🎭 KBS专业频道
- **KBS DRAMA** - KBS电视剧频道
- **KBS JOY** - KBS娱乐频道
- **KBS STORY** - KBS故事频道
- **KBS LIFE** - KBS生活频道

## 🔗 播放列表地址
https://raw.githubusercontent.com/GoonhoLee/korean-tv-static/main/korean_tv.m3u
### 备用地址
https://gist.githubusercontent.com/GoonhoLee/1eefb097a9b3ec25c79bbd4149066d41/raw/korean_tv.m3u

## 🚀 使用方法

### 1. 在播放器中使用
- **VLC Media Player**: 媒体 → 打开网络串流 → 粘贴上述URL
- **PotPlayer**: 打开 → 打开链接 → 粘贴URL
- **Kodi**: 添加到PVR客户端
- **Tivimate**: 添加M3U播放列表

### 2. 在代码中使用
```python
import requests

url = "https://raw.githubusercontent.com/GoonhoLee/korean-tv-static/main/korean_tv.m3u"
response = requests.get(url)
playlist_content = response.text

🔄 更新频率
自动更新: 每48小时（UTC时间0点）

手动触发: 支持通过GitHub Actions手动立即更新

实时监控: 自动检测源失效并切换备用源

⚠️ 免责声明
本项目仅提供技术研究和学习使用

所有直播源均来自官方公开渠道

请遵守当地法律法规，合理使用资源

不保证所有源的长期稳定性和可用性

🤝 贡献
欢迎提交Issue和Pull Request来改进项目！

报告失效的播放源

建议新的频道源

改进代码和文档

📄 许可证
本项目采用 MIT 许可证 - 查看 LICENSE 文件了解详情。
