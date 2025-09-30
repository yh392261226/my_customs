"""
修复对话框文件中的super().on_mount()调用问题
ModalScreen可能没有on_mount方法，需要移除super()调用
"""

import os
import re
from typing import List

def find_dialog_files_with_super_calls() -> List[str]:
    """查找有super().on_mount()调用的对话框文件"""
    dialog_files = []
    dialogs_dir = "src/ui/dialogs"
    
    if os.path.exists(dialogs_dir):
        for file in os.listdir(dialogs_dir):
            if file.endswith('.py') and not file.startswith('__'):
                file_path = os.path.join(dialogs_dir, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if 'super().on_mount()' in content:
                        dialog_files.append(file_path)
                        
                except Exception as e:
                    print(f"读取文件失败 {file_path}: {e}")
    
    return dialog_files

def fix_super_call_in_file(file_path: str) -> bool:
    """修复文件中的super().on_mount()调用"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换super().on_mount()调用
        # 查找包含super().on_mount()的on_mount方法
        pattern = r'(def on_mount\(self\)[^:]*:\s*"""[^"]*"""\s*)super\(\)\.on_mount\(\)\s*'
        
        def replacement(match):
            method_start = match.group(1)
            return method_start
        
        fixed_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        
        # 如果没有匹配到上面的模式，尝试更简单的替换
        if fixed_content == content:
            fixed_content = content.replace('super().on_mount()\n        # 应用通用样式隔离', '# 应用通用样式隔离')
            fixed_content = fixed_content.replace('super().on_mount()\n        #', '#')
            fixed_content = fixed_content.replace('        super().on_mount()\n', '')
        
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
    print("🔧 开始修复对话框文件中的super().on_mount()调用问题...")
    
    dialog_files = find_dialog_files_with_super_calls()
    
    if not dialog_files:
        print("✅ 没有发现需要修复的对话框文件")
        return
    
    print(f"发现 {len(dialog_files)} 个需要修复的对话框文件")
    
    success_count = 0
    for file_path in dialog_files:
        print(f"  🔧 修复 {os.path.basename(file_path)}")
        
        if fix_super_call_in_file(file_path):
            if verify_file_syntax(file_path):
                print(f"    ✅ 修复成功")
                success_count += 1
            else:
                print(f"    ⚠️  修复完成但有语法问题")
        else:
            print(f"    ❌ 修复失败")
    
    print(f"🎉 修复完成！成功修复 {success_count}/{len(dialog_files)} 个文件")

if __name__ == "__main__":
    main()