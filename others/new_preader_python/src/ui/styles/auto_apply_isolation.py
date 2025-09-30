"""
自动应用样式隔离脚本
为所有屏幕和对话框自动添加样式隔离支持
"""

import os
import re
from typing import List, Tuple

def find_all_screen_files() -> List[str]:
    """查找所有屏幕文件"""
    screen_files = []
    screens_dir = "src/ui/screens"
    
    if os.path.exists(screens_dir):
        for file in os.listdir(screens_dir):
            if file.endswith('.py') and not file.startswith('__'):
                screen_files.append(os.path.join(screens_dir, file))
    
    return screen_files

def find_all_dialog_files() -> List[str]:
    """查找所有对话框文件"""
    dialog_files = []
    dialogs_dir = "src/ui/dialogs"
    
    if os.path.exists(dialogs_dir):
        for file in os.listdir(dialogs_dir):
            if file.endswith('.py') and not file.startswith('__'):
                dialog_files.append(os.path.join(dialogs_dir, file))
    
    return dialog_files

def analyze_file(file_path: str) -> Tuple[bool, bool, str]:
    """分析文件是否需要添加样式隔离
    
    Returns:
        (needs_import, needs_isolation, class_name)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有样式隔离导入
        has_isolation_import = (
            'universal_style_isolation' in content or
            'apply_universal_style_isolation' in content or
            'comprehensive_style_isolation' in content
        )
        
        # 查找类定义
        class_pattern = r'class\s+(\w+)\s*\([^)]*(?:Screen|ModalScreen)[^)]*\):'
        class_match = re.search(class_pattern, content)
        
        if not class_match:
            return False, False, ""
        
        class_name = class_match.group(1)
        
        # 检查是否已经有样式隔离调用
        has_isolation_call = (
            'apply_universal_style_isolation' in content or
            'apply_comprehensive_style_isolation' in content or
            '@universal_style_isolation' in content
        )
        
        needs_import = not has_isolation_import
        needs_isolation = not has_isolation_call
        
        return needs_import, needs_isolation, class_name
        
    except Exception as e:
        print(f"分析文件失败 {file_path}: {e}")
        return False, False, ""

def add_isolation_to_file(file_path: str, class_name: str) -> bool:
    """为文件添加样式隔离支持"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        modified_lines = []
        import_added = False
        isolation_added = False
        
        for i, line in enumerate(lines):
            # 添加导入语句
            if not import_added and line.startswith('from src.') and 'import' in line:
                modified_lines.append(line)
                # 在最后一个src导入后添加样式隔离导入
                if i + 1 < len(lines) and not lines[i + 1].startswith('from src.'):
                    modified_lines.append('from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation')
                    import_added = True
                continue
            
            # 在on_mount方法中添加样式隔离调用
            if not isolation_added and 'def on_mount(self)' in line:
                modified_lines.append(line)
                # 查找方法体的缩进
                indent = len(line) - len(line.lstrip())
                # 添加样式隔离调用
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if '"""' in next_line or 'super().on_mount()' in next_line:
                        # 在文档字符串或super调用后添加
                        modified_lines.append(next_line)
                        if i + 2 < len(lines) and 'super().on_mount()' in lines[i + 2]:
                            modified_lines.append(lines[i + 2])
                            i += 1
                        modified_lines.append(' ' * (indent + 4) + '# 应用通用样式隔离')
                        modified_lines.append(' ' * (indent + 4) + 'apply_universal_style_isolation(self)')
                        isolation_added = True
                        i += 1
                        continue
                    else:
                        # 直接在方法开始处添加
                        modified_lines.append(' ' * (indent + 4) + '# 应用通用样式隔离')
                        modified_lines.append(' ' * (indent + 4) + 'apply_universal_style_isolation(self)')
                        isolation_added = True
                continue
            
            # 如果没有on_mount方法，在类定义后添加
            if not isolation_added and f'class {class_name}' in line and ':' in line:
                modified_lines.append(line)
                # 查找类的缩进
                class_indent = len(line) - len(line.lstrip())
                # 添加on_mount方法
                modified_lines.append('')
                modified_lines.append(' ' * (class_indent + 4) + 'def on_mount(self) -> None:')
                modified_lines.append(' ' * (class_indent + 8) + '"""组件挂载时应用样式隔离"""')
                modified_lines.append(' ' * (class_indent + 8) + 'super().on_mount()')
                modified_lines.append(' ' * (class_indent + 8) + '# 应用通用样式隔离')
                modified_lines.append(' ' * (class_indent + 8) + 'apply_universal_style_isolation(self)')
                isolation_added = True
                continue
            
            modified_lines.append(line)
        
        # 如果还没有添加导入，在文件开头添加
        if not import_added:
            # 找到最后一个import语句的位置
            import_index = -1
            for i, line in enumerate(modified_lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_index = i
            
            if import_index >= 0:
                modified_lines.insert(import_index + 1, 'from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation')
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(modified_lines))
        
        return True
        
    except Exception as e:
        print(f"修改文件失败 {file_path}: {e}")
        return False

def apply_isolation_to_all_files():
    """为所有文件应用样式隔离"""
    print("🎨 开始为所有屏幕和对话框应用通用样式隔离...")
    
    # 处理屏幕文件
    screen_files = find_all_screen_files()
    print(f"📱 找到 {len(screen_files)} 个屏幕文件")
    
    for file_path in screen_files:
        needs_import, needs_isolation, class_name = analyze_file(file_path)
        if needs_import or needs_isolation:
            print(f"  🔧 修改 {os.path.basename(file_path)} (类: {class_name})")
            if add_isolation_to_file(file_path, class_name):
                print(f"    ✅ 成功")
            else:
                print(f"    ❌ 失败")
        else:
            print(f"  ⏭️  跳过 {os.path.basename(file_path)} (已有样式隔离)")
    
    # 处理对话框文件
    dialog_files = find_all_dialog_files()
    print(f"💬 找到 {len(dialog_files)} 个对话框文件")
    
    for file_path in dialog_files:
        needs_import, needs_isolation, class_name = analyze_file(file_path)
        if needs_import or needs_isolation:
            print(f"  🔧 修改 {os.path.basename(file_path)} (类: {class_name})")
            if add_isolation_to_file(file_path, class_name):
                print(f"    ✅ 成功")
            else:
                print(f"    ❌ 失败")
        else:
            print(f"  ⏭️  跳过 {os.path.basename(file_path)} (已有样式隔离)")
    
    print("🎉 样式隔离应用完成！")

if __name__ == "__main__":
    apply_isolation_to_all_files()