#!/usr/bin/env python3
"""
将 design.md 转换为带样式的 HTML 文件
"""
import markdown
import re
from pathlib import Path

# 读取 Markdown 文件
md_file = Path("design.md")
html_file = Path("design.html")

with open(md_file, "r", encoding="utf-8") as f:
    md_content = f.read()

# 转换为 HTML
html_body = markdown.markdown(
    md_content,
    extensions=["fenced_code", "tables", "codehilite"]
)

# 处理 Mermaid 代码块：将 ```mermaid 代码块转换为 Mermaid div
def replace_mermaid_blocks(html):
    import html as html_module
    
    # 匹配 <pre class="codehilite"><code class="language-mermaid">...</code></pre> 格式
    pattern = r'<pre[^>]*><code[^>]*class="language-mermaid"[^>]*>(.*?)</code></pre>'
    
    def replace_func(match):
        mermaid_code = match.group(1)
        # 解码 HTML 实体
        mermaid_code = html_module.unescape(mermaid_code)
        # 移除多余的空白和换行
        mermaid_code = '\n'.join(line.strip() for line in mermaid_code.split('\n') if line.strip())
        return f'<div class="mermaid">\n{mermaid_code}\n</div>'
    
    html = re.sub(pattern, replace_func, html, flags=re.DOTALL)
    
    return html

html_body = replace_mermaid_blocks(html_body)

# 创建完整的 HTML 文档，包含典雅的样式
html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>设计文档 - Agentic 结构感知代码索引系统</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Helvetica, Arial, sans-serif;
            background-color: #4a4a4a;
            color: #2c2c2c;
            line-height: 1.7;
            padding: 40px 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background-color: #f5f5f5;
            border-radius: 16px;
            padding: 60px 50px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        
        h1 {{
            color: #1a1a1a;
            font-size: 2.2em;
            margin-bottom: 20px;
            font-weight: 600;
            border-bottom: 2px solid #d0d0d0;
            padding-bottom: 15px;
        }}
        
        h2 {{
            color: #2a2a2a;
            font-size: 1.8em;
            margin-top: 40px;
            margin-bottom: 20px;
            font-weight: 600;
            padding-top: 10px;
        }}
        
        h3 {{
            color: #333;
            font-size: 1.4em;
            margin-top: 30px;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        
        h4 {{
            color: #444;
            font-size: 1.2em;
            margin-top: 25px;
            margin-bottom: 12px;
            font-weight: 600;
        }}
        
        p {{
            margin-bottom: 16px;
            text-align: justify;
        }}
        
        ul, ol {{
            margin-left: 25px;
            margin-bottom: 20px;
        }}
        
        li {{
            margin-bottom: 10px;
        }}
        
        strong {{
            color: #1a1a1a;
            font-weight: 600;
        }}
        
        code {{
            background-color: #e8e8e8;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Code", "Droid Sans Mono", "Source Code Pro", monospace;
            font-size: 0.9em;
            color: #c7254e;
        }}
        
        pre {{
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 20px 0;
            box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.2);
        }}
        
        pre code {{
            background-color: transparent;
            color: #f8f8f2;
            padding: 0;
        }}
        
        blockquote {{
            border-left: 4px solid #999;
            padding-left: 20px;
            margin: 20px 0;
            color: #555;
            font-style: italic;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: #fff;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        
        th {{
            background-color: #e8e8e8;
            font-weight: 600;
        }}
        
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 30px 0;
        }}
        
        /* Mermaid 图表样式 */
        .mermaid {{
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</head>
<body>
    <div class="container">
        {html_body}
    </div>
</body>
</html>"""

# 保存 HTML 文件
with open(html_file, "w", encoding="utf-8") as f:
    f.write(html_template)

print(f"✓ 已成功将 {md_file} 转换为 {html_file}")

