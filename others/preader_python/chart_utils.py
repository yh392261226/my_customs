import tempfile
import subprocess
import sys
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress
from datetime import datetime, timedelta

# 导入语言包功能
sys.path.insert(0, os.path.dirname(__file__))
from lang import get_text

def create_daily_stats_chart(daily_stats, title_key="daily_stats", lang="zh"):
    """创建每日阅读统计图表"""
    console = Console()
    title = get_text(title_key, lang)
    
    # 创建表格
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column(get_text("date", lang), style="dim", width=12)
    table.add_column(get_text("reading_time_minutes", lang), justify="right")
    table.add_column(get_text("chart", lang), width=30)
    
    # 找出最大值用于缩放图表
    max_minutes = max(minutes for _, minutes in daily_stats) if daily_stats else 1
    
    for date, minutes in daily_stats:
        # 创建简单的条形图
        bar_length = int(minutes * 30 / max_minutes)
        bar = "█" * bar_length + "░" * (30 - bar_length)
        
        table.add_row(
            date,
            f"{minutes}",
            f"{bar} {minutes}{get_text('minutes', lang)}"
        )
    
    return table

def create_weekly_stats_chart(weekly_stats, title_key="weekly_stats", lang="zh"):
    """创建每周阅读统计图表"""
    console = Console()
    title = get_text(title_key, lang)
    
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column(get_text("week", lang), style="dim", width=12)
    table.add_column(get_text("reading_time_minutes", lang), justify="right")
    table.add_column(get_text("chart", lang), width=30)
    
    max_minutes = max(minutes for _, minutes in weekly_stats) if weekly_stats else 1
    
    for week, minutes in weekly_stats:
        bar_length = int(minutes * 30 / max_minutes)
        bar = "█" * bar_length + "░" * (30 - bar_length)
        
        table.add_row(
            week,
            f"{minutes}",
            f"{bar} {minutes}{get_text('minutes', lang)}"
        )
    
    return table

def create_monthly_stats_chart(monthly_stats, title_key="monthly_stats", lang="zh"):
    """创建每月阅读统计图表"""
    console = Console()
    title = get_text(title_key, lang)
    
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column(get_text("month", lang), style="dim", width=12)
    table.add_column(get_text("reading_time_minutes", lang), justify="right")
    table.add_column(get_text("chart", lang), width=30)
    
    max_minutes = max(minutes for _, minutes in monthly_stats) if monthly_stats else 1
    
    for month, minutes in monthly_stats:
        bar_length = int(minutes * 30 / max_minutes)
        bar = "█" * bar_length + "░" * (30 - bar_length)
        
        table.add_row(
            month,
            f"{minutes}",
            f"{bar} {minutes}{get_text('minutes', lang)}"
        )
    
    return table

def create_summary_panel(stats, title_key="every_day_stats", lang="zh"):
    """创建统计摘要面板"""
    if not stats:
        return Panel(get_text("none_data", lang), title=get_text(title_key, lang))
    
    total_minutes = sum(minutes for _, minutes in stats)
    avg_minutes = total_minutes / len(stats) if stats else 0
    max_minutes = max(minutes for _, minutes in stats) if stats else 0
    min_minutes = min(minutes for _, minutes in stats) if stats else 0
    
    summary_text = Text()
    summary_text.append(f"{get_text('total', lang)}: {total_minutes} {get_text('minutes', lang)}\n", style="bold")
    summary_text.append(f"{get_text('avg', lang)}: {avg_minutes:.1f} {get_text('minutes', lang)}/{get_text('cycle', lang)}\n")
    summary_text.append(f"{get_text('highest', lang)}: {max_minutes} {get_text('minutes', lang)}\n")
    summary_text.append(f"{get_text('lowest', lang)}: {min_minutes} {get_text('minutes', lang)}\n")
    summary_text.append(f"{get_text('cycle_count', lang)}: {len(stats)}")
    
    return Panel(summary_text, title=get_text(title_key, lang))

def show_rich_stats(daily_stats, weekly_stats, monthly_stats, book_title=None, lang="zh"):
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
    title = f"📊 {get_text('stats', lang)}"
    if book_title:
        title += f" - {book_title}"
    
    layout["header"].update(
        Panel(Text(title, justify="center", style="bold yellow"), style="on blue")
    )
    
    # 每日统计
    daily_table = create_daily_stats_chart(daily_stats[-10:], "nearly_ten_days", lang)  # 只显示最近10天
    layout["daily"].update(daily_table)
    
    # 每周统计
    weekly_table = create_weekly_stats_chart(weekly_stats[-8:], "nearly_eight_weeks", lang)  # 只显示最近8周
    layout["weekly"].update(weekly_table)
    
    # 每月统计
    monthly_table = create_monthly_stats_chart(monthly_stats[-12:], "nearly_tweleve_month", lang)  # 只显示最近12个月
    layout["monthly"].update(monthly_table)
    
    # 底部摘要
    summary_panel = create_summary_panel(daily_stats, "every_day_stats", lang)
    layout["footer"].update(summary_panel)
    
    # 显示所有内容
    console.print(layout)
    
    # 显示操作提示
    console.print(f"\n{get_text('press_enter_to_back', lang)}...", style="bold dim")

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