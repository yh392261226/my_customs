"""
全面修复自动应用脚本产生的所有问题
"""

import os
import re
from typing import List, Tuple

def find_all_problematic_files() -> List[str]:
    """查找所有有问题的文件"""
    problematic_files = []
    
    # 检查屏幕文件
    for root, dirs, files in os.walk("src/ui"):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                file_path = os.path.join(root, file)
                if has_structural_problems(file_path):
                    problematic_files.append(file_path)
    
    return problematic_files

def has_structural_problems(file_path: str) -> bool:
    """检查文件是否有结构问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有重复的类定义
        class_definitions = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
        if len(class_definitions) != len(set(class_definitions)):
            return True
        
        # 检查是否有类定义在方法内部
        lines = content.split('\n')
        in_method = False
        method_indent = 0
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith('def ') and ':' in stripped:
                in_method = True
                method_indent = len(line) - len(line.lstrip())
                continue
            
            if in_method and stripped.startswith('class ') and ':' in stripped:
                current_indent = len(line) - len(line.lstrip())
                if current_indent > method_indent:
                    return True
            
            if in_method and line.strip() and not line.startswith(' ' * (method_indent + 1)):
                in_method = False
        
        return False
        
    except Exception:
        return False

def fix_file_completely(file_path: str) -> bool:
    """完全修复文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 分析文件结构
        lines = original_content.split('\n')
        
        # 提取导入部分
        imports = []
        class_content = []
        current_section = "imports"
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            if current_section == "imports":
                if stripped.startswith(('import ', 'from ')) or stripped == '' or stripped.startswith('#') or stripped.startswith('"""'):
                    imports.append(line)
                elif stripped.startswith('class '):
                    current_section = "class"
                    class_content.append(line)
                else:
                    imports.append(line)
            elif current_section == "class":
                # 检查是否是有问题的on_mount方法
                if 'def on_mount(self)' in line:
                    class_content.append(line)
                    i += 1
                    
                    # 添加方法体，直到遇到类定义或文件结束
                    while i < len(lines):
                        current_line = lines[i]
                        
                        # 如果遇到新的类定义，停止
                        if current_line.strip().startswith('class ') and ':' in current_line:
                            # 不要重复添加类定义
                            break
                        elif current_line.strip().startswith('"""') and 'class' not in current_line:
                            # 跳过错位的文档字符串
                            i += 1
                            continue
                        else:
                            class_content.append(current_line)
                            i += 1
                    
                    continue
                else:
                    class_content.append(line)
            
            i += 1
        
        # 重新组装文件
        fixed_content = '\n'.join(imports + class_content)
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        return True
        
    except Exception as e:
        print(f"修复文件失败 {file_path}: {e}")
        return False

def verify_file_syntax(file_path: str) -> bool:
    """验证文件语法是否正确"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尝试编译检查语法
        compile(content, file_path, 'exec')
        return True
        
    except SyntaxError as e:
        print(f"语法错误 {file_path}: {e}")
        return False
    except Exception as e:
        print(f"验证失败 {file_path}: {e}")
        return False

def main():
    """主修复函数"""
    print("🔧 开始全面修复自动应用脚本产生的问题...")
    
    problematic_files = find_all_problematic_files()
    
    if not problematic_files:
        print("✅ 没有发现需要修复的文件")
        return
    
    print(f"发现 {len(problematic_files)} 个需要修复的文件")
    
    for file_path in problematic_files:
        print(f"  🔧 修复 {file_path}")
        
        if fix_file_completely(file_path):
            if verify_file_syntax(file_path):
                print(f"    ✅ 修复成功")
            else:
                print(f"    ⚠️  修复完成但有语法问题")
        else:
            print(f"    ❌ 修复失败")
    
    print("🎉 全面修复完成！")

if __name__ == "__main__":
    main()