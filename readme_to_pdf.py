# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-10-25 23:10:57
# File:readme_to_pdf.py
import os
import re
import sys
import shutil
import tempfile
import subprocess

from markdown_it import MarkdownIt

from . import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(PROJECT_ROOT, 'README.md')
PDF_PATH = os.path.join(PROJECT_ROOT, 'res', '使用必读.pdf')
CHROME_CANDIDATES = [
    os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
    os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
]
LIGHT_CSS = '''
@page {
  size: A4;
  margin: 0;
}
* {
  box-sizing: border-box;
}
html, body {
  margin: 0;
  padding: 0;
  background: #ffffff;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
body {
  font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', Arial, sans-serif;
  font-size: 11.5px;
  line-height: 1.7;
  color: #1f2328;
  word-wrap: break-word;
}
.readme-body {
  max-width: 100%;
  padding: 12mm 10mm;
}
h1, h2, h3, h4 {
  margin: 1.2em 0 0.6em;
  font-weight: 600;
  line-height: 1.3;
}
h1 {
  font-size: 22px;
  padding-bottom: 8px;
  border-bottom: 1px solid #d0d7de;
}
h2 {
  font-size: 18px;
  margin-top: 2em;
  padding-bottom: 6px;
  border-bottom: 1px solid #d8dee4;
}
h3 {
  font-size: 15px;
}
h4 {
  font-size: 13px;
}
p {
  margin: 0 0 10px;
}
a {
  color: #0969da;
  text-decoration: none;
  word-break: break-all;
}
img {
  max-width: 100%;
  height: auto;
  vertical-align: middle;
}
ul, ol {
  margin: 0 0 10px;
  padding-left: 24px;
}
li {
  margin: 3px 0;
}
blockquote {
  margin: 0 0 10px;
  padding: 8px 14px;
  border-left: 4px solid #d0d7de;
  background: #f6f8fa;
  color: #59636e;
}
code {
  font-family: 'Cascadia Mono', Consolas, 'Courier New', monospace;
  font-size: 11px;
  padding: 2px 5px;
  background: #eff1f3;
  border-radius: 4px;
}
pre {
  margin: 0 0 12px;
  padding: 12px;
  overflow: hidden;
  background: #f6f8fa;
  border-radius: 6px;
}
pre code {
  display: block;
  padding: 0;
  background: transparent;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
}
table {
  width: 100%;
  margin: 0 0 12px;
  border-collapse: collapse;
  font-size: 10.5px;
}
th, td {
  padding: 5px 8px;
  border: 1px solid #d0d7de;
  text-align: left;
  vertical-align: top;
}
th {
  background: #f6f8fa;
  font-weight: 600;
}
details {
  margin: 0 0 12px;
  padding: 8px 12px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
}
details > summary {
  color: #0969da;
  font-weight: 600;
  cursor: default;
}
hr {
  margin: 18px 0;
  border: 0;
  border-top: 1px solid #d8dee4;
}
.markdown-alert {
  margin: 0 0 12px;
  padding: 10px 14px;
  border-left: 4px solid #d0d7de;
  border-radius: 6px;
  background: #f6f8fa;
}
.markdown-alert-title {
  margin: 0 0 6px;
  font-weight: 600;
}
.markdown-alert p:not(.markdown-alert-title) {
  margin: 0;
}
.markdown-alert-note {
  border-left-color: #0969da;
}
.markdown-alert-note .markdown-alert-title {
  color: #0969da;
}
.markdown-alert-tip {
  border-left-color: #1f883d;
}
.markdown-alert-tip .markdown-alert-title {
  color: #1f883d;
}
.markdown-alert-important {
  border-left-color: #8250df;
}
.markdown-alert-important .markdown-alert-title {
  color: #8250df;
}
.markdown-alert-warning {
  border-left-color: #9a6700;
}
.markdown-alert-warning .markdown-alert-title {
  color: #9a6700;
}
.markdown-alert-caution {
  border-left-color: #cf222e;
}
.markdown-alert-caution .markdown-alert-title {
  color: #cf222e;
}
'''
DARK_CSS = '''
@page {
  size: A4;
  margin: 0;
}
* {
  box-sizing: border-box;
}
html, body {
  margin: 0;
  padding: 0;
  background: #0d1117;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
body {
  font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', Arial, sans-serif;
  font-size: 11.5px;
  line-height: 1.7;
  color: #e6edf3;
  word-wrap: break-word;
}
.readme-body {
  max-width: 100%;
  padding: 12mm 10mm;
}
h1, h2, h3, h4 {
  margin: 1.2em 0 0.6em;
  font-weight: 600;
  line-height: 1.3;
  color: #e6edf3;
}
h1 {
  font-size: 22px;
  padding-bottom: 8px;
  border-bottom: 1px solid #21262d;
}
h2 {
  font-size: 18px;
  margin-top: 2em;
  padding-bottom: 6px;
  border-bottom: 1px solid #21262d;
}
h3 {
  font-size: 15px;
}
h4 {
  font-size: 13px;
}
p {
  margin: 0 0 10px;
}
a {
  color: #58a6ff;
  text-decoration: none;
  word-break: break-all;
}
img {
  max-width: 100%;
  height: auto;
  vertical-align: middle;
  border: 1px solid #30363d;
  border-radius: 6px;
}
ul, ol {
  margin: 0 0 10px;
  padding-left: 24px;
}
li {
  margin: 3px 0;
}
blockquote {
  margin: 0 0 10px;
  padding: 8px 14px;
  border-left: 4px solid #3b434b;
  color: #9198a1;
}
code {
  font-family: 'Cascadia Mono', Consolas, 'Courier New', monospace;
  font-size: 11px;
  padding: 2px 5px;
  background: rgba(110, 118, 129, 0.4);
  border-radius: 4px;
}
pre {
  margin: 0 0 12px;
  padding: 12px;
  overflow: hidden;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
}
pre code {
  display: block;
  padding: 0;
  background: transparent;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
}
table {
  width: 100%;
  margin: 0 0 12px;
  border-collapse: collapse;
  font-size: 10.5px;
}
th, td {
  padding: 5px 8px;
  border: 1px solid #30363d;
  text-align: left;
  vertical-align: top;
}
th {
  background: #161b22;
  font-weight: 600;
}
tr:nth-child(even) td {
  background: #161b22;
}
details {
  margin: 0 0 12px;
  padding: 8px 12px;
  border: 1px solid #30363d;
  border-radius: 6px;
}
details > summary {
  color: #58a6ff;
  font-weight: 600;
  cursor: default;
}
hr {
  margin: 18px 0;
  border: 0;
  border-top: 1px solid #21262d;
}
.markdown-alert {
  margin: 0 0 12px;
  padding: 10px 14px;
  border-left: 4px solid #30363d;
  border-radius: 6px;
  background: #161b22;
}
.markdown-alert-title {
  margin: 0 0 6px;
  font-weight: 600;
}
.markdown-alert p:not(.markdown-alert-title) {
  margin: 0;
}
.markdown-alert-note {
  border-left-color: #4493f8;
}
.markdown-alert-note .markdown-alert-title {
  color: #4493f8;
}
.markdown-alert-tip {
  border-left-color: #3fb950;
}
.markdown-alert-tip .markdown-alert-title {
  color: #3fb950;
}
.markdown-alert-important {
  border-left-color: #ab7df8;
}
.markdown-alert-important .markdown-alert-title {
  color: #ab7df8;
}
.markdown-alert-warning {
  border-left-color: #d29922;
}
.markdown-alert-warning .markdown-alert-title {
  color: #d29922;
}
.markdown-alert-caution {
  border-left-color: #f85149;
}
.markdown-alert-caution .markdown-alert-title {
  color: #f85149;
}
'''
THEME_CSS = {
    'dark': DARK_CSS,
    'light': LIGHT_CSS,
}
DEFAULT_THEME = 'dark'
GITHUB_ALERT_STYLES = {
    'note': ('ℹ️', '说明'),
    'tip': ('💡', '提示'),
    'important': ('❗', '重要'),
    'warning': ('⚠️', '警告'),
    'caution': ('⛔', '当心'),
}
GITHUB_ALERT_PATTERN = re.compile(r'<blockquote>\s*<p>\[!(\w+)\]\s*\n?(.*?)</p>\s*</blockquote>', re.DOTALL)
RELEASE_BADGE_PATTERN = re.compile(r'<img src="https://img\.shields\.io/github/v/release/[^"]*" alt="Release">')
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>TRMD使用必读</title>
<style>{css}</style>
</head>
<body>
<article class="readme-body">{body}</article>
</body>
</html>
'''


def read_project_version():
    '''读取module/__init__.py中的版本号。'''
    init_path = os.path.join(PROJECT_ROOT, 'module', '__init__.py')
    with open(init_path, 'r', encoding='UTF-8') as init_file:
        matched = re.search(r"^__version__\s*=\s*'([^']+)'", init_file.read(), re.MULTILINE)
    if matched is None:
        logging.error('未能从module/__init__.py读取到__version__。')
        return None
    return matched.group(1)


def replace_github_alert(match):
    '''把引用块形式的GitHub提示块渲染为带图标与标题的提示卡片。'''
    alert_type = match.group(1).lower()
    icon, title = GITHUB_ALERT_STYLES.get(alert_type, ('ℹ️', alert_type.capitalize()))
    content = match.group(2).strip()
    return f'<div class="markdown-alert markdown-alert-{alert_type}"><p class="markdown-alert-title">{icon} {title}</p><p>{content}</p></div>'


def render_readme_html(readme_path, theme=DEFAULT_THEME):
    '''读取README.md并渲染为打印用的完整HTML。'''
    with open(readme_path, 'r', encoding='UTF-8') as readme_file:
        markdown_text = readme_file.read()
    project_version = read_project_version()
    if project_version is not None:
        # 把动态获取的release徽章硬替换为代码版本号,避免显示的版本滞留在上一个已发布版本。
        static_badge = f'<img src="https://img.shields.io/badge/release-v{project_version}-F1C40F?style=flat-square" alt="Release">'
        markdown_text = RELEASE_BADGE_PATTERN.sub(static_badge, markdown_text)
    converter = MarkdownIt('commonmark').enable('table')
    body = converter.render(markdown_text)
    # 给折叠块补上open属性，等价于在控制台执行展开全部details。
    body = re.sub(r'<details>', '<details open>', body)
    body = GITHUB_ALERT_PATTERN.sub(replace_github_alert, body)
    return HTML_TEMPLATE.format(css=THEME_CSS[theme], body=body)


def find_chrome():
    '''查找本机谷歌浏览器可执行文件。'''
    for chrome_path in CHROME_CANDIDATES:
        if os.path.isfile(chrome_path):
            return chrome_path
    logging.error(f'未找到谷歌浏览器,已尝试路径:"{CHROME_CANDIDATES}"。')
    return None


def export_html_to_pdf(html_path, pdf_path, chrome_path):
    '''调用谷歌浏览器无头模式把HTML打印为PDF。'''
    file_url = 'file:///' + html_path.replace(os.sep, '/')
    profile_dir = tempfile.mkdtemp(prefix='trmd_readme_pdf_')
    command = [
        chrome_path,
        '--headless=new',
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        f'--user-data-dir={profile_dir}',
        '--run-all-compositor-stages-before-draw',
        '--virtual-time-budget=30000',
        '--no-pdf-header-footer',
        f'--print-to-pdf={pdf_path}',
        file_url,
    ]
    subprocess.run(command, timeout=300, check=False)
    shutil.rmtree(profile_dir, ignore_errors=True)


def main():
    '''把README.md导出为res/使用必读.pdf,可传入主题参数dark或light。'''
    theme = DEFAULT_THEME
    if len(sys.argv) > 1 and sys.argv[1] in THEME_CSS:
        theme = sys.argv[1]
    chrome_path = find_chrome()
    if chrome_path is None:
        return
    html = render_readme_html(README_PATH, theme)
    html_fd, html_path = tempfile.mkstemp(prefix='trmd_readme_', suffix='.html')
    os.close(html_fd)
    with open(html_path, 'w', encoding='UTF-8') as html_file:
        html_file.write(html)
    logging.info(f'已生成临时HTML:"{html_path}"。')
    export_html_to_pdf(html_path, PDF_PATH, chrome_path)
    os.remove(html_path)
    if os.path.isfile(PDF_PATH):
        logging.info(f'已导出PDF:"{PDF_PATH}"。')
    else:
        logging.error('导出失败,未生成PDF。')
