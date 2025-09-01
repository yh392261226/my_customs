import tempfile
import subprocess
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress
from datetime import datetime, timedelta

def create_daily_stats_chart(daily_stats, title="每日阅读统计"):
    """创建每日阅读统计图表"""
    console = Console()
    
    # 创建表格
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("日期", style="dim", width=12)
    table.add_column("阅读时间(分钟)", justify="right")
    table.add_column("图表", width=30)
    
    # 找出最大值用于缩放图表
    max_minutes = max(minutes for _, minutes in daily_stats) if daily_stats else 1
    
    for date, minutes in daily_stats:
        # 创建简单的条形图
        bar_length = int(minutes * 30 / max_minutes)
        bar = "█" * bar_length + "░" * (30 - bar_length)
        
        table.add_row(
            date,
            f"{minutes}",
            f"{bar} {minutes}分钟"
        )
    
    return table

def create_weekly_stats_chart(weekly_stats, title="每周阅读统计"):
    """创建每周阅读统计图表"""
    console = Console()
    
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("周次", style="dim", width=12)
    table.add_column("阅读时间(分钟)", justify="right")
    table.add_column("图表", width=30)
    
    max_minutes = max(minutes for _, minutes in weekly_stats) if weekly_stats else 1
    
    for week, minutes in weekly_stats:
        bar_length = int(minutes * 30 / max_minutes)
        bar = "█" * bar_length + "░" * (30 - bar_length)
        
        table.add_row(
            week,
            f"{minutes}",
            f"{bar} {minutes}分钟"
        )
    
    return table

def create_monthly_stats_chart(monthly_stats, title="每月阅读统计"):
    """创建每月阅读统计图表"""
    console = Console()
    
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("月份", style="dim", width=12)
    table.add_column("阅读时间(分钟)", justify="right")
    table.add_column("图表", width=30)
    
    max_minutes = max(minutes for _, minutes in monthly_stats) if monthly_stats else 1
    
    for month, minutes in monthly_stats:
        bar_length = int(minutes * 30 / max_minutes)
        bar = "█" * bar_length + "░" * (30 - bar_length)
        
        table.add_row(
            month,
            f"{minutes}",
            f"{bar} {minutes}分钟"
        )
    
    return table

def create_summary_panel(stats, title="阅读统计摘要"):
    """创建统计摘要面板"""
    if not stats:
        return Panel("暂无统计数据", title=title)
    
    total_minutes = sum(minutes for _, minutes in stats)
    avg_minutes = total_minutes / len(stats) if stats else 0
    max_minutes = max(minutes for _, minutes in stats) if stats else 0
    min_minutes = min(minutes for _, minutes in stats) if stats else 0
    
    summary_text = Text()
    summary_text.append(f"总计: {total_minutes} 分钟\n", style="bold")
    summary_text.append(f"平均: {avg_minutes:.1f} 分钟/周期\n")
    summary_text.append(f"最高: {max_minutes} 分钟\n")
    summary_text.append(f"最低: {min_minutes} 分钟\n")
    summary_text.append(f"周期数: {len(stats)}")
    
    return Panel(summary_text, title=title)

def show_rich_stats(daily_stats, weekly_stats, monthly_stats, book_title=None):
    """使用Rich显示完整的统计图表"""
    console = Console()
    
    # 创建布局
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=7)
    )
    
    layout["main"].split_row(
        Layout(name="daily", ratio=1),
        Layout(name="weekly", ratio=1),
        Layout(name="monthly", ratio=1)
    )
    
    # 头部标题
    title = "📊 阅读统计"
    if book_title:
        title += f" - {book_title}"
    
    layout["header"].update(
        Panel(Text(title, justify="center", style="bold yellow"), style="on blue")
    )
    
    # 每日统计
    daily_table = create_daily_stats_chart(daily_stats[-10:], "最近10天")  # 只显示最近10天
    layout["daily"].update(daily_table)
    
    # 每周统计
    weekly_table = create_weekly_stats_chart(weekly_stats[-8:], "最近8周")  # 只显示最近8周
    layout["weekly"].update(weekly_table)
    
    # 每月统计
    monthly_table = create_monthly_stats_chart(monthly_stats[-12:], "最近12个月")  # 只显示最近12个月
    layout["monthly"].update(monthly_table)
    
    # 底部摘要
    summary_panel = create_summary_panel(daily_stats, "每日统计摘要")
    layout["footer"].update(summary_panel)
    
    # 显示所有内容
    console.print(layout)
    
    # 显示操作提示
    console.print("\n按任意键返回阅读器...", style="bold dim")

def display_rich_chart_in_terminal():
    """在终端中显示Rich图表（通过子进程）"""
    # 创建一个临时Python脚本来显示Rich图表
    temp_script = """
import sys
sys.path.insert(0, '/path/to/your/script/directory')  # 需要替换为实际路径

from chart_utils import show_rich_stats

# 这里需要从某个地方获取统计数据
# 假设我们已经有了这些数据
daily_stats = []  # 需要替换为实际数据
weekly_stats = []  # 需要替换为实际数据
monthly_stats = []  # 需要替换为实际数据
book_title = None  # 需要替换为实际数据

show_rich_stats(daily_stats, weekly_stats, monthly_stats, book_title)
input("按回车键返回...")
"""
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(temp_script)
        temp_file = f.name
    
    try:
        # 运行临时脚本
        subprocess.run([sys.executable, temp_file], cwd=os.path.dirname(__file__))
    finally:
        # 删除临时文件
        os.unlink(temp_file)