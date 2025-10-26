# 解析器重构指南 - 配置驱动版本

## 概述

本指南详细说明了如何将现有的解析器重构为基于配置驱动的新版本。新版本使用继承和属性配置，显著减少了代码重复，提高了可维护性。

## 重构步骤

### 1. 创建新的解析器文件

为每个解析器创建新的文件，文件名格式为 `{原文件名}_v2.py`：

```bash
# 示例
cp crxs.py crxs_v2.py
cp 87nb.py 87nb_v2.py
```

### 2. 导入基类并定义类

```python
"""
{网站名称} 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class {原类名}Parser(BaseParser):
    """{网站名称} 小说解析器 - 配置驱动版本"""
```

### 3. 定义配置属性

#### 基本信息
```python
# 基本信息
name = "{网站名称}"
description = "{网站名称} 小说解析器"
base_url = "{网站基础URL}"
```

#### 正则表达式配置
```python
# 正则表达式配置
title_reg = [
    r'<h1[^>]*>(.*?)</h1>',  # 标题正则1
    r'<title>(.*?)</title>'  # 标题正则2
]

content_reg = [
    r'<div[^>]*class="content"[^>]*>(.*?)</div>',  # 内容正则1
    r'<div[^>]*id="content"[^>]*>(.*?)</div>'      # 内容正则2
]

status_reg = [
    r'状态[:：]\s*(.*?)[<\s]',  # 状态正则1
    r'status[:：]\s*(.*?)[<\s]'  # 状态正则2
]
```

#### 处理函数配置
```python
# 处理函数配置
after_crawler_func = [
    "_clean_html_content",  # 公共基类提供的HTML清理
    "_remove_ads"           # 子类特有的广告移除
]
```

### 4. 重写必要的方法

#### URL生成方法
```python
def get_novel_url(self, novel_id: str) -> str:
    """
    重写URL生成方法，适配网站的URL格式
    
    Args:
        novel_id: 小说ID
        
    Returns:
        小说URL
    """
    return f"{self.base_url}/book/{novel_id}.html"
```

#### 书籍类型检测
```python
def _detect_book_type(self, content: str) -> str:
    """
    重写书籍类型检测，适配网站的特定模式
    
    Args:
        content: 页面内容
        
    Returns:
        书籍类型
    """
    # 网站特定的多章节检测模式
    if '章节列表' in content or 'chapter-list' in content:
        return "多章节"
    
    return "短篇"
```

#### 多章节解析逻辑
```python
def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
    """
    实现多章节小说解析逻辑
    
    Args:
        content: 页面内容
        novel_url: 小说URL
        title: 小说标题
        
    Returns:
        小说详情信息
    """
    # 提取章节链接
    chapter_links = self._extract_chapter_links(content)
    if not chapter_links:
        raise Exception("无法提取章节列表")
    
    print(f"发现 {len(chapter_links)} 个章节")
    
    # 创建小说内容
    novel_content = {
        'title': title,
        'author': self.name,
        'novel_id': self._extract_novel_id_from_url(novel_url),
        'url': novel_url,
        'chapters': []
    }
    
    # 抓取所有章节内容
    self._get_all_chapters(chapter_links, novel_content)
    
    return novel_content
```

#### 章节链接提取
```python
def _extract_chapter_links(self, content: str) -> List[Dict[str, str]]:
    """
    提取章节链接列表 - 网站特定实现
    
    Args:
        content: 页面内容
        
    Returns:
        章节链接列表
    """
    import re
    chapter_links = []
    
    # 网站特定的章节链接模式
    pattern = r'<a href="(/book/\d+/\d+\.html)"[^>]*>(.*?)</a>'
    matches = re.findall(pattern, content)
    
    for href, title in matches:
        chapter_links.append({
            'url': href,
            'title': title.strip()
        })
    
    return chapter_links
```

#### 特有处理函数
```python
def _remove_ads(self, content: str) -> str:
    """
    移除广告内容 - 网站特有处理
    
    Args:
        content: 原始内容
        
    Returns:
        处理后的内容
    """
    import re
    
    # 移除网站常见的广告模式
    ad_patterns = [
        r'<div class="ad".*?</div>',
        r'<!--.*?广告.*?-->',
        r'赞助.*?内容'
    ]
    
    for pattern in ad_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
    
    return content
```

### 5. 列表页解析（可选）

```python
def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
    """
    解析小说列表页 - 大多数网站不需要列表页解析
    
    Args:
        url: 小说列表页URL
        
    Returns:
        小说信息列表
    """
    return []
```

## 重构示例

### 原始代码 vs 重构后代码

**原始代码 (约400-500行)**：
- 大量重复的网络请求代码
- 硬编码的正则表达式
- 复杂的错误处理逻辑

**重构后代码 (约100-150行)**：
- 继承基类，复用公共功能
- 配置驱动的正则表达式
- 简洁的特有逻辑实现

## 测试验证

### 1. 单元测试

使用 `parser_tester.py` 进行功能测试：

```python
from src.spiders.parser_tester import test_all_parsers

# 运行所有测试
test_results = test_all_parsers()
```

### 2. 性能监控

使用性能监控工具监控解析器性能：

```python
from src.spiders.performance_monitor import monitor_decorator

# 使用装饰器监控方法
@monitor_decorator("解析器名称")
def parse_novel_detail(self, novel_id: str):
    # 解析逻辑
    pass
```

## 已重构的解析器

- ✅ `crxs_v2.py` - crxs.me 解析器
- ✅ `87nb_v2.py` - 87NB小说网解析器  
- ✅ `book18_v2.py` - book18.me 解析器
- ✅ `xchina_v2.py` - xchina.co 解析器
- ✅ `91porna_v2.py` - 91porna.com 解析器
- ✅ `h528_v2.py` - h528.com 解析器
- ✅ `xbookcn_v2.py` - xbookcn.com 解析器

## 待重构的解析器

- ⏳ `renqixiaoshuo.py` - 人气小说网解析器
- ⏳ `custom.py` - 自定义解析器

## 集成测试

运行集成测试脚本验证所有重构后的解析器：

```bash
cd /Users/yanghao/data/app/python/newreader
python src/spiders/integration_test.py
```

## 性能对比

| 指标 | 原始版本 | 重构版本 | 改进 |
|------|----------|----------|------|
| 代码行数 | 400-500行 | 100-150行 | 减少70% |
| 重复代码 | 大量 | 极少 | 减少90% |
| 维护难度 | 高 | 低 | 显著降低 |
| 扩展性 | 差 | 优秀 | 显著提升 |

## 注意事项

1. **正则表达式优化**：根据具体网站结构调整正则表达式
2. **错误处理**：确保特有逻辑的错误处理完善
3. **性能测试**：验证重构后性能没有下降
4. **功能验证**：确保所有原有功能正常工作

## 下一步

1. 完成剩余解析器的重构
2. 优化正则表达式配置
3. 进行全面的集成测试
4. 部署到生产环境