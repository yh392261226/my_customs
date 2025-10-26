# 解析器重构指南

## 概述

本文档指导如何将现有的书籍网站解析器重构为使用新的 `BaseParser` 基类，以实现代码复用和简化扩展。

## 重构步骤

### 1. 导入基类

在现有解析器文件的开头添加导入语句：

```python
from .base_parser import BaseParser
```

### 2. 修改类定义

将现有的解析器类改为继承自 `BaseParser`：

```python
# 修改前
class RenqixiaoshuoParser:
    
# 修改后
class RenqixiaoshuoParser(BaseParser):
```

### 3. 删除重复代码

删除以下重复的方法（这些方法已经在基类中实现）：

- `__init__` 方法（如果只是设置基本属性）
- `_get_url_content` 方法
- `_clean_content` 方法
- `save_to_file` 方法

### 4. 添加必要的方法

确保实现以下抽象方法：

```python
def _get_base_url(self) -> str:
    """返回基础URL"""
    return "https://www.example.com"

def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
    """解析小说列表页"""
    # 大多数网站不需要列表解析，返回空列表即可
    return []

def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
    """获取书籍首页的标题、简介与状态"""
    # 实现具体的提取逻辑

def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
    """解析小说详情并抓取小说内容"""
    # 实现具体的解析逻辑
```

### 5. 利用基类提供的方法

使用基类提供的便利方法：

- `self._get_url_content(url)` - 获取URL内容
- `self._clean_content(html)` - 清理HTML内容
- `self._extract_title(content)` - 提取标题（可重写）
- `self._extract_content(content)` - 提取内容（可重写）

## 重构示例

### 重构前（87nb.py 示例）

```python
class Nb87Parser:
    name = "87NB小说网"
    description = "87NB小说网整本小说爬取解析器"
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        self.base_url = "https://www.87nb.com"
        self.session = requests.Session()
        self.chapter_count = 0
        self.proxy_config = proxy_config or {'enabled': False, 'proxy_url': ''}
        # ... 设置请求头等代码
    
    def _get_url_content(self, url: str, max_retries: int = 5) -> Optional[str]:
        # ... 重复的实现
    
    def _clean_content(self, html_content: str) -> str:
        # ... 重复的实现
    
    def save_to_file(self, novel_content: Dict[str, Any], storage_folder: str) -> str:
        # ... 重复的实现
```

### 重构后

```python
from .base_parser import BaseParser

class Nb87Parser(BaseParser):
    name = "87NB小说网"
    description = "87NB小说网整本小说爬取解析器"
    
    def _get_base_url(self) -> str:
        return "https://www.87nb.com"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        return []  # 不需要列表解析
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        # 使用基类方法简化实现
        novel_url = f"{self.base_url}/lt/{novel_id}.html"
        content = self._get_url_content(novel_url)
        if not content:
            return None
        # ... 具体的提取逻辑
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        # 使用基类方法简化实现
        novel_url = f"{self.base_url}/lt/{novel_id}.html"
        content = self._get_url_content(novel_url)
        if not content:
            raise Exception(f"无法获取小说详情页: {novel_url}")
        # ... 具体的解析逻辑
```

## 优势

### 代码复用
- 所有解析器共享相同的网络请求逻辑
- 统一的HTML内容清理方法
- 标准化的文件保存功能

### 简化扩展
- 新增解析器只需实现核心业务逻辑
- 基类提供默认实现，减少重复代码
- 统一的接口规范

### 维护性
- 公共逻辑集中管理
- 错误修复和功能改进只需修改基类
- 更好的代码组织结构

## 注意事项

1. **向后兼容**：工厂函数支持新旧两种解析器格式
2. **渐进式重构**：可以逐个解析器进行重构，不影响现有功能
3. **测试验证**：重构后需要验证解析器功能正常

## 下一步

建议按照以下顺序重构现有解析器：

1. 87nb.py
2. renqixiaoshuo.py  
3. book18.py
4. crxs.py
5. xchina.py
6. 91porna.py
7. h528.py
8. xbookcn.py

每个解析器重构完成后，都需要进行功能测试以确保正常工作。