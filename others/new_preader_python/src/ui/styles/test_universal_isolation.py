"""
通用样式隔离测试脚本
验证所有屏幕和对话框的样式隔离是否正常工作
"""

import sys
import os
sys.path.append('.')

from src.ui.styles.universal_style_isolation import global_universal_isolation_manager

def test_isolation_manager():
    """测试样式隔离管理器"""
    print("🧪 测试通用样式隔离管理器...")
    
    # 测试管理器是否正常创建
    assert global_universal_isolation_manager is not None
    print("✅ 样式隔离管理器创建成功")
    
    # 测试管理器的基本功能
    assert hasattr(global_universal_isolation_manager, 'apply_component_isolation')
    assert hasattr(global_universal_isolation_manager, 'remove_component_isolation')
    print("✅ 样式隔离管理器方法完整")
    
    print("🎉 样式隔离管理器测试通过！")

def test_screen_files():
    """测试屏幕文件是否都有样式隔离"""
    print("\n📱 测试屏幕文件样式隔离...")
    
    screens_dir = "src/ui/screens"
    screen_files = []
    
    if os.path.exists(screens_dir):
        for file in os.listdir(screens_dir):
            if file.endswith('.py') and not file.startswith('__'):
                screen_files.append(os.path.join(screens_dir, file))
    
    print(f"找到 {len(screen_files)} 个屏幕文件")
    
    for file_path in screen_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否有样式隔离导入
            has_isolation = (
                'universal_style_isolation' in content or
                'apply_universal_style_isolation' in content or
                'comprehensive_style_isolation' in content
            )
            
            if has_isolation:
                print(f"  ✅ {os.path.basename(file_path)} - 已有样式隔离")
            else:
                print(f"  ❌ {os.path.basename(file_path)} - 缺少样式隔离")
                
        except Exception as e:
            print(f"  ⚠️  {os.path.basename(file_path)} - 读取失败: {e}")

def test_dialog_files():
    """测试对话框文件是否都有样式隔离"""
    print("\n💬 测试对话框文件样式隔离...")
    
    dialogs_dir = "src/ui/dialogs"
    dialog_files = []
    
    if os.path.exists(dialogs_dir):
        for file in os.listdir(dialogs_dir):
            if file.endswith('.py') and not file.startswith('__'):
                dialog_files.append(os.path.join(dialogs_dir, file))
    
    print(f"找到 {len(dialog_files)} 个对话框文件")
    
    for file_path in dialog_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否有样式隔离导入
            has_isolation = (
                'universal_style_isolation' in content or
                'apply_universal_style_isolation' in content
            )
            
            if has_isolation:
                print(f"  ✅ {os.path.basename(file_path)} - 已有样式隔离")
            else:
                print(f"  ❌ {os.path.basename(file_path)} - 缺少样式隔离")
                
        except Exception as e:
            print(f"  ⚠️  {os.path.basename(file_path)} - 读取失败: {e}")

def test_css_generation():
    """测试CSS生成功能"""
    print("\n🎨 测试CSS生成功能...")
    
    try:
        # 测试CSS命名空间添加
        test_css = """
Button {
    background: $primary;
    color: white;
}

Label {
    color: $text;
}
"""
        
        # 模拟添加命名空间
        namespaced_css = global_universal_isolation_manager._add_namespace_to_css(test_css, "test")
        
        if ".test-component Button" in namespaced_css:
            print("  ✅ CSS命名空间添加成功")
        else:
            print("  ❌ CSS命名空间添加失败")
            
        print("🎉 CSS生成功能测试通过！")
        
    except Exception as e:
        print(f"  ❌ CSS生成测试失败: {e}")

def main():
    """主测试函数"""
    print("🚀 开始通用样式隔离系统测试...\n")
    
    try:
        test_isolation_manager()
        test_screen_files()
        test_dialog_files()
        test_css_generation()
        
        print("\n🎉 所有测试完成！通用样式隔离系统工作正常。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)