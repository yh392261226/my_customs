#!/bin/bash
# 使用 stty 获取终端大小并确保程序使用全屏
export LINES=$(tput lines)
export COLUMNS=$(tput cols)
# 自动运行Python程序并处理错误

# 1. 检查Python版本
PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
	PYTHON_CMD="python"
	if ! command -v python &>/dev/null; then
		echo "错误: 未找到Python解释器"
		exit 1
	fi
fi

# 2. 检查依赖
echo "检查Python依赖..."
$PYTHON_CMD -c "
try:
    import textual
    import rich
    import sqlite3
    print('所有依赖已安装')
except ImportError as e:
    print(f'缺少依赖: {e}')
    exit(1)
" || exit 1

# 3. 创建日志目录
LOG_DIR="$HOME/.config/new_preader/logs"
mkdir -p "$LOG_DIR"

# 4. 运行程序并捕获错误
echo "启动NewReader..."
$PYTHON_CMD main.py 2>&1 | tee "$LOG_DIR/run_$(date +%Y%m%d_%H%M%S).log"

# 5. 检查退出状态
EXIT_CODE=${PIPESTATUS[0]}
case $EXIT_CODE in
0) echo "程序正常退出" ;;
1) echo "错误: 配置错误" ;;
2) echo "错误: 依赖缺失" ;;
3) echo "错误: 文件权限问题" ;;
*) echo "程序异常退出 (代码: $EXIT_CODE)" ;;
esac

exit $EXIT_CODE
