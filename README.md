
## 🔧 技术实现

### 核心技术栈
- **Python 3.9+**：主要脚本语言
- **Selenium**：自动化浏览器操作，处理动态加载内容
- **Chrome Headless**：无头浏览器运行环境
- **GitHub Actions**：自动化工作流，定时执行
- **webdriver-manager**：自动管理 ChromeDriver 版本

### 工作流程
1. **定时触发**：每天 UTC 19:00（中国时间次日 03:00）自动运行
2. **频道抓取**：
   - KBS 频道：深度分析页面获取认证参数，提取带签名的 M3U8 链接
   - MBN 频道：同时获取高画质（1000k）和标清（600k）两个版本
3. **播放列表生成**：按频道分类生成标准 M3U8 格式文件
4. **多平台同步**：自动推送到 GitHub 和 Gitee 仓库

### KBS 频道抓取特点
- ✅ 自动处理页面广告等待
- ✅ 多层级深度解析：HTML 源码 → JavaScript 变量 → 网络请求监控
- ✅ 智能认证参数提取（Policy、Signature、Key-Pair-Id）
- ✅ 多重回退机制确保抓取成功率

### MBN 频道抓取特点
- ✅ 双画质版本支持（高画质 + 标清）
- ✅ 自动认证链接解析
- ✅ 备用链接兜底机制

## 📊 更新频率

- **自动更新**：每日 1 次（北京时间凌晨 3:00）
- **手动更新**：支持通过 GitHub Actions 手动触发
- **即时更新**：修改 `update_playlist.py` 文件时自动触发

## 🌐 镜像站点

| 平台 | 仓库地址 | 用途 |
|------|---------|------|
| GitHub | [GoonhoLee/korean-tv-static](https://github.com/GoonhoLee/korean-tv-static) | 主要仓库 |
| Gitee | [GoonhoLee/korean-tv-static](https://gitee.com/GoonhoLee/korean-tv-static) | 国内镜像 |

## 📝 注意事项

### 网络要求
- 🔒 **KBS 频道**：需要能访问 `gscdn.kbs.co.kr`
- 🔒 **JTBC 频道**：需要韩国 IP 地址才能播放
- 🔒 **MBN 频道**：需要能访问 `hls-live.mbn.co.kr`
- ✅ **其他频道**：大部分无特殊网络要求

### 播放建议
- 🕐 更新时间为北京时间凌晨，建议在更新后 1-2 小时使用
- 📡 部分频道可能需要特定地区的网络环境
- 🔄 直播链接具有时效性，建议使用最新版本的播放列表
- ⚡ 高画质频道可能需要更稳定的网络连接

## 🤝 贡献指南

欢迎提交 Issue 或 Pull Request！

### 报告问题
如果发现频道无法播放，请提供：
1. 具体的频道名称
2. 错误信息或截图
3. 您的网络环境（地区、是否使用 VPN）

### 添加新频道
1. Fork 本仓库
2. 在 `CHANNELS` 配置中添加新频道信息
3. 实现对应的抓取逻辑
4. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## ⚠️ 免责声明

本项目仅供学习和研究使用，请遵守相关法律法规：
- 本项目的所有内容仅用于技术研究和学习目的
- 请尊重电视台的版权和合法权益
- 使用者应自行承担使用风险
- 本项目不对播放内容的可用性和合法性负责

## 📞 联系方式

- **Issues**：[GitHub Issues](https://github.com/GoonhoLee/korean-tv-static/issues)
- **Gitee Issues**：[Gitee Issues](https://gitee.com/GoonhoLee/korean-tv-static/issues)

---

<div align="center">
  <p>如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！</p>
  <p>Made with ❤️ for Korean TV enthusiasts</p>
</div>
