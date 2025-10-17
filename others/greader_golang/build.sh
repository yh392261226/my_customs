#!/bin/bash

# 优化构建脚本 - 终端小说阅读器
echo "📖 构建终端小说阅读器..."

# 清理之前的构建
echo "🧹 清理旧文件..."
rm -f novel-reader

# 检查依赖
echo "📦 检查依赖..."
go mod tidy

# 构建
echo "🔨 构建程序..."
go build -ldflags="-s -w" -o novel-reader main.go

# 检查构建是否成功
if [ $? -eq 0 ]; then
    echo "✅ 构建成功！"
    echo "📁 可执行文件: novel-reader"
    
    # 显示文件信息
    if command -v file &> /dev/null; then
        echo "📊 文件信息:"
        file novel-reader
        echo "📏 文件大小: $(du -h novel-reader | cut -f1)"
    fi
    
    # 测试运行
    echo "🧪 测试运行..."
    ./novel-reader --version
else
    echo "❌ 构建失败！"
    exit 1
fi