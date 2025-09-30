"""
修复自动应用脚本产生的错误
"""

import os
import re
from typing import List

def find_broken_files() -> List[str]:
    """查找有问题的文件"""
    broken_files = []
    
    # 检查屏幕文件
    screens_dir = "src/ui/screens"
    if os.path.exists(screens_dir):
        for file in os.listdir(screens_dir):
            if file.endswith('.py') and not file.startswith('__'):
                file_path = os.path.join(screens_dir, file)
                if check_file_structure(file_path):
                    broken_files.append(file_path)
    
    # 检查对话框文件
    dialogs_dir = "src/ui/dialogs"
    if os.path.exists(dialogs_dir):
        for file in os.listdir(dialogs_dir):
            if file.endswith('.py') and not file.startswith('__'):
                file_path = os.path.join(dialogs_dir, file)
                if check_file_structure(file_path):
                    broken_files.append(file_path)
    
    return broken_files

def check_file_structure(file_path: str) -> bool:
    """检查文件结构是否有问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有类定义在方法内部的问题
        lines = content.split('\n')
        in_method = False
        method_indent = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 检测方法开始
            if stripped.startswith('def ') and ':' in stripped:
                in_method = True
                method_indent = len(line) - len(line.lstrip())
                continue
            
            # 如果在方法内部发现类定义，说明有问题
            if in_method and stripped.startswith('class ') and ':' in stripped:
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= method_indent:
                    in_method = False
                else:
                    print(f"发现问题文件: {file_path} - 第{i+1}行: 类定义在方法内部")
                    return True
            
            # 检测方法结束
            if in_method and line.strip() and not line.startswith(' ' * (method_indent + 1)):
                in_method = False
        
        return False
        
    except Exception as e:
        print(f"检查文件失败 {file_path}: {e}")
        return False

def fix_file_structure(file_path: str) -> bool:
    """修复文件结构"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # 检查是否是有问题的on_mount方法
            if 'def on_mount(self)' in line and i + 1 < len(lines):
                # 添加方法定义
                fixed_lines.append(line)
                i += 1
                
                # 添加方法体
                while i < len(lines) and (lines[i].startswith('    ') or lines[i].strip() == ''):
                    current_line = lines[i]
                    
                    # 如果遇到类定义，说明方法体结束了
                    if current_line.strip().startswith('class ') and ':' in current_line:
                        # 确保类定义在正确的缩进级别
                        fixed_lines.append('')  # 添加空行分隔
                        fixed_lines.append(current_line)
                        i += 1
                        break
                    elif current_line.strip().startswith('"""') and 'class' not in current_line:
                        # 这是方法的文档字符串，跳过
                        i += 1
                        continue
                    else:
                        fixed_lines.append(current_line)
                        i += 1
                
                continue
            
            fixed_lines.append(line)
            i += 1
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(fixed_lines))
        
        return True
        
    except Exception as e:
        print(f"修复文件失败 {file_path}: {e}")
        return False

def fix_all_broken_files():
    """修复所有有问题的文件"""
    print("🔧 开始修复自动应用脚本产生的错误...")
    
    broken_files = find_broken_files()
    
    if not broken_files:
        print("✅ 没有发现需要修复的文件")
        return
    
    print(f"发现 {len(broken_files)} 个需要修复的文件")
    
    for file_path in broken_files:
        print(f"  🔧 修复 {os.path.basename(file_path)}")
        if fix_file_structure(file_path):
            print(f"    ✅ 修复成功")
        else:
            print(f"    ❌ 修复失败")
    
    print("🎉 文件修复完成！")

if __name__ == "__main__":
    fix_all_broken_files()