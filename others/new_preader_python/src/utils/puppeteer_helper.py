"""
Puppeteer助手函数，用于获取JavaScript渲染后的页面内容
"""

import subprocess
import json
import time
from typing import Optional

def get_puppeteer_content(url: str, timeout: int = 30) -> Optional[str]:
    """
    使用Puppeteer获取JavaScript渲染后的页面内容
    
    Args:
        url: 目标URL
        timeout: 超时时间（秒）
        
    Returns:
        渲染后的HTML内容或None
    """
    try:
        # 创建一个临时的Node.js脚本来获取内容
        script = f"""
const puppeteer = require('puppeteer');

async function getContent() {{
    let browser;
    try {{
        browser = await puppeteer.launch({{
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--window-size=1920,1080'
            ]
        }});
        
        const page = await browser.newPage();
        await page.setViewport({{ width: 1920, height: 1080 }});
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36');
        
        await page.goto('{url}', {{ 
            waitUntil: 'networkidle2',
            timeout: {timeout * 1000}
        }});
        
        // 等待内容加载
        await page.waitForTimeout(3000);
        
        const content = await page.content();
        await browser.close();
        
        return content;
    }} catch (error) {{
        if (browser) {{
            await browser.close();
        }}
        throw error;
    }}
}}

getContent().then(content => {{
    console.log(JSON.stringify({{ success: true, content }}));
}}).catch(error => {{
    console.log(JSON.stringify({{ success: false, error: error.message }}));
}});
"""
        
        # 将脚本写入临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            # 执行脚本
            result = subprocess.run(
                ['node', script_path],
                capture_output=True,
                text=True,
                timeout=timeout + 10
            )
            
            if result.returncode == 0:
                # 解析JSON输出
                output = json.loads(result.stdout.strip())
                if output.get('success'):
                    return output.get('content')
                else:
                    print(f"Puppeteer错误: {output.get('error')}")
                    return None
            else:
                print(f"脚本执行失败: {result.stderr}")
                return None
                
        finally:
            # 清理临时文件
            import os
            try:
                os.unlink(script_path)
            except:
                pass
                
    except Exception as e:
        print(f"获取Puppeteer内容时出错: {e}")
        return None