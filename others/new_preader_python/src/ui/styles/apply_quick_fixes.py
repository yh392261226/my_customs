"""
应用快速修复脚本
自动为现有屏幕应用样式隔离
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)

def find_screen_files() -> List[Path]:
    """查找所有屏幕文件"""
    screens_dir = Path(__file__).parent.parent / "screens"
    screen_files = []
    
    if screens_dir.exists():
        for file_path in screens_dir.glob("*_screen.py"):
            screen_files.append(file_path)
    
    return screen_files

def add_isolation_import(file_path: Path) -> bool:
    """为屏幕文件添加隔离导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有隔离导入
        if 'quick_fix_isolation' in content:
            logger.info(f"文件 {file_path.name} 已经有隔离导入")
            return False
        
        # 查找合适的位置添加导入
        import_pattern = r'(from src\.ui\.styles\..*import.*\n)'
        if re.search(import_pattern, content):
            # 在现有样式导入后添加
            new_import = "from src.ui.styles.quick_fix_isolation import quick_isolation_decorator\n"
            content = re.sub(import_pattern, r'\1' + new_import, content, count=1)
        else:
            # 在其他导入后添加
            import_section_end = content.rfind('from src.')
            if import_section_end != -1:
                # 找到导入行的结尾
                line_end = content.find('\n', import_section_end)
                if line_end != -1:
                    new_import = "\nfrom src.ui.styles.quick_fix_isolation import quick_isolation_decorator\n"
                    content = content[:line_end] + new_import + content[line_end:]
        
        # 在文件末尾添加装饰器应用
        class_pattern = r'class (\w+Screen)\([^)]+\):'
        matches = re.findall(class_pattern, content)
        
        if matches:
            screen_class = matches[0]  # 取第一个匹配的屏幕类
            decorator_code = f"\n# 应用样式隔离\n{screen_class} = quick_isolation_decorator({screen_class})\n"
            content += decorator_code
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"为文件 {file_path.name} 添加了样式隔离")
        return True
        
    except Exception as e:
        logger.error(f"处理文件 {file_path.name} 时出错: {e}")
        return False

def update_css_paths(file_path: Path) -> bool:
    """更新CSS路径以包含隔离样式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有basic_isolation.css
        if 'basic_isolation.css' in content:
            logger.info(f"文件 {file_path.name} 已经包含隔离样式")
            return False
        
        # 查找CSS_PATH定义
        css_path_pattern = r'CSS_PATH\s*=\s*["\']([^"\']+)["\']'
        match = re.search(css_path_pattern, content)
        
        if match:
            original_path = match.group(1)
            # 替换为列表形式
            new_css_path = f'''CSS_PATH = [
        "{original_path}",
        "../styles/basic_isolation.css"
    ]'''
            content = re.sub(css_path_pattern, new_css_path, content)
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"为文件 {file_path.name} 更新了CSS路径")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"更新CSS路径时出错 {file_path.name}: {e}")
        return False

def apply_quick_fixes() -> Tuple[int, int]:
    """应用快速修复到所有屏幕文件"""
    screen_files = find_screen_files()
    success_count = 0
    total_count = len(screen_files)
    
    logger.info(f"找到 {total_count} 个屏幕文件")
    
    for file_path in screen_files:
        try:
            logger.info(f"处理文件: {file_path.name}")
            
            # 添加隔离导入和装饰器
            import_added = add_isolation_import(file_path)
            
            # 更新CSS路径
            css_updated = update_css_paths(file_path)
            
            if import_added or css_updated:
                success_count += 1
                logger.info(f"成功处理文件: {file_path.name}")
            else:
                logger.info(f"文件无需修改: {file_path.name}")
                
        except Exception as e:
            logger.error(f"处理文件失败 {file_path.name}: {e}")
    
    return success_count, total_count

def create_backup() -> bool:
    """创建屏幕文件的备份"""
    try:
        screens_dir = Path(__file__).parent.parent / "screens"
        backup_dir = screens_dir.parent / "screens_backup"
        
        if backup_dir.exists():
            logger.warning("备份目录已存在，跳过备份")
            return True
        
        # 创建备份目录
        backup_dir.mkdir(exist_ok=True)
        
        # 复制所有屏幕文件
        for file_path in screens_dir.glob("*.py"):
            backup_path = backup_dir / file_path.name
            backup_path.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')
        
        logger.info(f"已创建备份到: {backup_dir}")
        return True
        
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始应用样式隔离快速修复")
    
    # 创建备份
    if create_backup():
        logger.info("备份创建成功")
    else:
        logger.warning("备份创建失败，继续执行修复")
    
    # 应用修复
    success_count, total_count = apply_quick_fixes()
    
    logger.info(f"修复完成: {success_count}/{total_count} 个文件已处理")
    
    if success_count > 0:
        logger.info("请重启应用程序以使修复生效")
    else:
        logger.info("所有文件都已是最新状态")

if __name__ == "__main__":
    main()