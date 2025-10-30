name: Update M3U Playlist

on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:
  push:
    paths:
      - 'update_playlist.py'
      - '.github/workflows/update_playlist.yml'

permissions:
  contents: write

jobs:
  update-playlist:
    runs-on: ubuntu-latest
    
    concurrency:
      group: ${{ github.workflow }}-${{ github.ref }}
      cancel-in-progress: true
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      with:
        token: ${{ secrets.GITHUB_TOKEN }}
        fetch-depth: 0
        
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests selenium beautifulsoup4
        
    - name: Install Chrome and ChromeDriver
      uses: browser-actions/setup-chrome@v1
      
    - name: Run playlist update script
      env:
        GITHUB_TOKEN: ${{ secrets.GIST_TOKEN }}
      run: |
        python update_playlist.py
        
    - name: Configure Git and commit changes
      env:
        GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      run: |
        # 配置Git用户
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        
        # 先拉取最新的远程更改（在添加本地更改之前）
        echo "📥 拉取最新的远程更改..."
        git pull origin main
        
        # 添加本地更改到暂存区
        echo "📦 添加本地更改..."
        git add -A
        
        # 检查是否有更改需要提交
        if git diff --staged --quiet; then
          echo "✅ 没有需要提交的更改"
          exit 0
        fi
        
        # 提交更改
        echo "💾 提交更改..."
        git commit -m "Auto-update playlist - $(date +'%Y-%m-%d %H:%M:%S')"
        
        # 推送更改
        echo "🚀 推送更改到远程仓库..."
        git push origin main
        
        echo "🎉 更改推送成功！"
