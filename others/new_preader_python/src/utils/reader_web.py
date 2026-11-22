"""
浏览器阅读器 Web 端资源
========================

本模块提供「局域网访问 + 在线/离线并存 + 手机/平板自适应」所需的前端资源，
全部以字符串常量形式提供，由两处消费：

* ``BrowserReader.create_reader_html()``：把 :data:`RESPONSIVE_CSS` /
  :data:`MOBILE_HTML` / :data:`READER_WEB_JS` 注入到原有的 file:// 单文件页面，
  因此桌面端行为完全不变，手机/平板只是多出响应式布局与独立设置页。
* ``BrowserReaderServerManager`` 的 ``/``、``/reader``、``/sw.js`` 路由：
  返回 :func:`build_portal_html` 生成的局域网书库入口页与 Service Worker。

设计要点
--------
* **同一个页面、同一套功能**：不区分「在线版 / 离线版」。页面始终可读
  （正文内嵌 HTML + IndexedDB 缓存），在线时自动同步书库/进度，后端关闭后
  自动降级为本地缓存，恢复在线后自动补传，用户无需切换任何模式。
* **动态后端地址**：HTTP 页面以 ``location.origin`` 为后端，``file://`` 页面
  沿用生成时注入的绝对地址，避免 ``0.0.0.0``/端口转发导致移动端连不上。
* **移动端设置独立页**：窄屏隐藏桌面工具栏，改为底部导航 + 全屏设置视图，
  复用阅读器现有的 ``changeFontSize`` / ``applySettings`` 等全局函数，不重写逻辑。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

# --------------------------------------------------------------------------- #
# 1. 响应式样式（桌面端零影响，全部规则包在 @media 内）
# --------------------------------------------------------------------------- #
RESPONSIVE_CSS = r"""
/* ===== 浏览器阅读器：平板 / 手机自适应（仅在窄屏生效） ===== */
.br-mobile-nav, .br-settings-view, .br-portal-offline-reader { display: none; }
/* 书库页顶部的「设置」入口：宽屏没有底部导航，用按钮打开同一个独立设置页 */
.br-portal-settings-btn { display: none; }

/* 局域网书库入口页的基础布局：必须对所有视口生效。
   之前误放在 max-width:768px 内，Pad / 桌面端会退化成无栅格、无卡片样式的裸列表。 */
.br-portal { max-width: 1100px; margin: 0 auto; padding: 16px; }
.br-portal-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.br-portal-head h1 { font-size: 20px; margin: 0; flex: 1 1 180px; }
.br-portal input[type=search] { width: 100%; box-sizing: border-box; min-height: 44px; padding: 8px 12px; border-radius: 10px; border: 1px solid var(--br-nav-border, #ddd); background: var(--br-card-bg, #fff); color: inherit; }
.br-portal .book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; margin-top: 12px; }
.br-portal .book-card { padding: 14px; border-radius: 12px; background: var(--br-card-bg, #fff); border: 1px solid var(--br-nav-border, #e6e6e6); cursor: pointer; }
.br-portal .book-card h3 { margin: 0 0 6px; font-size: 15px; word-break: break-all; }
.br-portal .book-card p { margin: 0; font-size: 12px; opacity: .65; }
.br-portal-empty { padding: 40px 12px; text-align: center; opacity: .65; }
.br-portal-offline-reader {
    position: fixed; inset: 0; z-index: 4500; overflow-y: auto;
    background: var(--reader-bg, var(--br-page-bg, #fff));
    color: var(--reader-text, var(--br-page-fg, #222));
}
.br-portal-offline-reader .br-offline-body { max-width: 820px; margin: 0 auto; padding: 20px 16px 100px; line-height: 1.8; word-wrap: break-word; }
.br-portal-offline-reader .br-offline-body img { max-width: 100%; height: auto; }
/* 本地书面板复用统一阅读工具栏：把返回按钮、书名、功能按钮整合到同一条 sticky 工具栏，
   避免桌面端出现「← 孤零零独占一行 + 标题另起一行」的割裂布局。 */
.br-offline-toolbar {
  position: sticky; top: 0; z-index: 2;
  display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  padding: 8px 12px; background: var(--br-card-bg, #fff);
  border-bottom: 1px solid var(--br-nav-border, #ddd);
}
.br-offline-toolbar button {
  cursor: pointer; padding: 5px 10px; border-radius: 14px;
  border: 1px solid var(--br-nav-border, #ddd);
  background: transparent; color: inherit; font-size: 13px;
}
.br-offline-toolbar button:hover { background: rgba(128,128,128,.12); }
.br-offline-toolbar #offlineBack { font-size: 18px; line-height: 1; }
.br-offline-toolbar .br-offline-title {
  flex: 1; min-width: 0; font-size: 15px; font-weight: 600; padding: 0 6px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

@media (max-width: 1024px) {
    html, body { -webkit-text-size-adjust: 100%; }
    body.br-web { max-width: 100% !important; padding-left: 16px !important; padding-right: 16px !important; }
    .br-web .toolbar { gap: 10px !important; padding: 8px 12px !important; overflow-x: auto; flex-wrap: nowrap !important; justify-content: flex-start !important; }
    /* 窄屏改为横向滚动：子项必须保持固有宽度且文字不换行，否则会被 flex 压成竖条、文字逐字换行 */
    .br-web .toolbar > * { flex: 0 0 auto !important; white-space: nowrap; }
    .br-web .settings-panel { max-width: min(680px, 94vw) !important; }
    .br-web .toc-container { width: 230px !important; }
}

@media (max-width: 768px) {
    /* 底部导航栏占位：所有贴底浮动元素统一按此偏移上移，避免互相遮挡。
       变量只在本媒体查询内定义，宽屏时不存在，桌面端自动回到各元素原始定位。 */
    :root {
        --br-nav-h: 64px;
        --br-nav-safe: env(safe-area-inset-bottom, 0px);
        --br-nav-offset: calc(var(--br-nav-h) + var(--br-nav-safe));
    }

    /* --- 正文：全宽、触屏友好 ---
       字号 / 行高必须完全交给阅读器设置（applySettings 写入 body 内联样式）。
       这里曾写死 17px / 1.8 并加 !important，内联样式优先级低于 !important，
       导致窄屏下 A+/A- 与设置页的字号、行高滑块全部失效；宽屏不受影响。
       默认值沿用主模板 body 的 18px / 1.8，加载后由 applySettings 覆盖。 */
    html.br-compact body, .br-web body {
        max-width: 100% !important;
        padding: 12px 14px calc(76px + var(--br-nav-safe)) 14px !important;
    }
    .br-compact .content, .br-web .content {
        margin-top: 12px !important; padding-bottom: 70px !important;
        max-width: 100% !important; word-wrap: break-word;
    }
    .br-compact .content img, .br-web .content img { max-width: 100% !important; height: auto !important; }

    /* --- 桌面专属浮层：手机端隐藏，改由底部导航 / 设置页提供入口 --- */
    .br-compact .toolbar, .br-web .toolbar,
    .br-compact .toolbar-toggle-container, .br-web .toolbar-toggle-container,
    .br-compact .minimap-container, .br-web .minimap-container,
    .br-compact .minimap-toggle, .br-web .minimap-toggle,
    .br-compact .keyboard-hint, .br-web .keyboard-hint,
    .br-compact .reading-stats, .br-web .reading-stats,
    .br-compact .reading-stats-enhanced, .br-web .reading-stats-enhanced,
    .br-compact .backend-port-badge, .br-web .backend-port-badge,
    .br-compact #nightModeToggle, .br-web #nightModeToggle,
    .br-compact #paginationModeToggle, .br-web #paginationModeToggle { display: none !important; }

    /* --- 编辑 / 锁屏 / 进度：手机上移到导航栏之上，不再盖住底部设置栏 ---
       原本 #brLockFab(bottom:16px) 与 #brEditFab(bottom:72px) 是 ID 选择器且
       z-index 高达 99999 / INT_MAX，会绘制在导航栏(z:3500)之上；桌面端这些
       规则不生效，自动恢复 16px / 72px。两者仍保持 56px 的原有间距。 */
    #brLockFab { bottom: calc(var(--br-nav-offset) + 12px) !important; }
    #brEditFab { bottom: calc(var(--br-nav-offset) + 68px) !important; }
    .br-compact .progress-info, .br-web .progress-info {
        bottom: calc(var(--br-nav-offset) + 16px) !important; right: 12px !important;
    }
    .br-compact .br-sync-panel, .br-web .br-sync-panel {
        bottom: calc(var(--br-nav-offset) + 12px) !important;
    }
    /* 导入指示器由 JS 写入内联 bottom，用 !important 覆盖 */
    #importFloatingIndicator { bottom: calc(var(--br-nav-offset) + 16px) !important; }

    /* --- 其余浮层改为贴边小按钮，偏移统一走变量（位置与原先一致） --- */
    /* 章节/书签按钮须高于右下角进度按钮(.progress-info: bottom nav+16px, 高约30px)，
       否则会被 z-index 更高的进度按钮盖住下半部分；这里上移到 nav+56px 留出间隙。 */
    .br-compact .toc-toggle-btn, .br-web .toc-toggle-btn {
        top: auto !important; bottom: calc(var(--br-nav-offset) + 56px) !important; right: 14px !important;
    }
    .br-compact .bookmark-btn, .br-web .bookmark-btn {
        top: auto !important; bottom: calc(var(--br-nav-offset) + 56px) !important; right: 68px !important;
    }
    .br-compact .auto-scroll-controls, .br-web .auto-scroll-controls,
    .br-compact .speech-controls, .br-web .speech-controls {
        left: 8px !important; right: 8px !important; width: auto !important;
        bottom: calc(var(--br-nav-offset) + 12px) !important;
        flex-wrap: wrap; justify-content: center;
    }

    /* --- 原有弹窗：手机端全屏化，避免 500px 居中框放不下 --- */
    .br-compact .settings-panel, .br-web .settings-panel {
        position: fixed !important; inset: 0 !important; transform: none !important;
        width: 100% !important; max-width: 100% !important; max-height: 100% !important;
        height: 100% !important; border: 0 !important; border-radius: 0 !important;
        overflow-y: auto !important; z-index: 3000 !important;
    }
    .br-compact .toc-container, .br-web .toc-container {
        position: fixed !important; inset: 0 0 0 auto !important;
        width: min(86vw, 340px) !important; top: 0 !important; right: 0 !important;
        height: 100% !important; max-height: 100% !important; z-index: 3100 !important;
    }
    .br-compact .search-container, .br-web .search-container {
        position: fixed !important; top: 8px !important; left: 8px !important; right: 8px !important;
        width: auto !important; z-index: 3200 !important;
    }
    .br-compact .pagination-controls, .br-web .pagination-controls {
        bottom: calc(var(--br-nav-offset) + 4px) !important;
        left: 8px !important; right: 8px !important; width: auto !important;
        justify-content: center;
    }
    /* 进度条贴在导航栏上沿，不占用导航栏本身 */
    .br-compact .progress-bar, .br-web .progress-bar { bottom: var(--br-nav-offset) !important; }
    .br-compact button, .br-web button,
    .br-compact select, .br-web select,
    .br-compact input[type=range], .br-web input[type=range] { min-height: 44px; }

    /* --- 底部导航（手机端主入口） --- */
    .br-mobile-nav {
        display: flex !important; position: fixed; left: 0; right: 0; bottom: 0;
        box-sizing: border-box; height: var(--br-nav-offset); z-index: 3500; align-items: stretch;
        background: var(--br-nav-bg, #ffffff); border-top: 1px solid var(--br-nav-border, #e2e4e8);
        padding-bottom: var(--br-nav-safe);
        box-shadow: 0 -2px 12px rgba(0,0,0,.08);
    }
    .br-mobile-nav button {
        flex: 1; border: 0; background: transparent; color: var(--br-nav-fg, #333);
        font-size: 12px; line-height: 1.2; display: flex; flex-direction: column;
        align-items: center; justify-content: center; gap: 3px; cursor: pointer;
    }
    .br-mobile-nav button .br-nav-icon { font-size: 20px; line-height: 1; }
    .br-mobile-nav button.active { color: #2f7cf6; font-weight: 700; }
    html.br-dark .br-mobile-nav { --br-nav-bg: #1c1e22; --br-nav-border: #333; --br-nav-fg: #e6e6e6; }

    /* --- 手机端独立设置页（全屏视图，不是浮层弹窗） --- */
    .br-settings-view {
        position: fixed; inset: 0; z-index: 4000; overflow-y: auto;
        background: var(--br-page-bg, #fafafa); color: var(--br-page-fg, #222);
        padding-bottom: calc(84px + env(safe-area-inset-bottom, 0px));
    }
    .br-settings-view.open { display: block !important; }
    .br-settings-head {
        position: sticky; top: 0; z-index: 2; display: flex; align-items: center; gap: 12px;
        padding: 12px 16px; background: inherit; border-bottom: 1px solid var(--br-nav-border, #e2e4e8);
    }
    .br-settings-head h2 { margin: 0; font-size: 18px; flex: 1; }
    .br-settings-head button { min-width: 44px; min-height: 44px; border: 0; background: transparent; color: inherit; font-size: 16px; }
    .br-settings-group { margin: 12px; padding: 14px; border-radius: 12px; background: var(--br-card-bg, #fff); box-shadow: 0 1px 3px rgba(0,0,0,.06); }
    .br-settings-group h3 { margin: 0 0 10px; font-size: 14px; opacity: .7; font-weight: 600; }
    .br-setting-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 48px; padding: 6px 0; border-bottom: 1px solid var(--br-nav-border, #eee); flex-wrap: wrap; }
    .br-setting-row:last-child { border-bottom: 0; }
    .br-setting-row > label { flex: 1 1 120px; font-size: 15px; }
    .br-setting-row select, .br-setting-row input[type=text], .br-setting-row input[type=password] {
        flex: 1 1 160px; min-height: 40px; padding: 6px 10px; border-radius: 8px;
        border: 1px solid var(--br-nav-border, #ddd); background: var(--br-card-bg, #fff); color: inherit;
    }
    .br-setting-row input[type=range] { flex: 1 1 160px; min-height: 40px; }
    .br-setting-row .br-value { font-size: 13px; opacity: .65; min-width: 42px; text-align: right; }
    .br-setting-actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .br-setting-actions button {
        flex: 1 1 45%; min-height: 44px; border-radius: 10px; border: 1px solid var(--br-nav-border, #ddd);
        background: var(--br-card-bg, #fff); color: inherit; font-size: 14px;
    }
    .br-setting-actions button.primary { background: #2f7cf6; border-color: #2f7cf6; color: #fff; }
    .br-net-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; padding: 5px 10px; border-radius: 999px; }
    .br-net-badge.online { background: rgba(46,160,67,.14); color: #2ea043; }
    .br-net-badge.offline { background: rgba(220,80,60,.14); color: #d4503c; }
    html.br-dark .br-settings-view { --br-page-bg: #141619; --br-page-fg: #e8e8e8; --br-card-bg: #202329; --br-nav-border: #333; }

    /* --- 书库入口页：手机端单列 + 底部留出导航栏空间 --- */
    .br-portal { padding: 12px 12px calc(84px + var(--br-nav-safe)); }
    .br-portal .book-grid { grid-template-columns: 1fr; }
}

/* 全屏覆盖层默认必须隐藏，只有显式加 .open 才显示。
   这两层带 position:fixed; inset:0 且 z-index 4000/4500，若在窄屏下
   默认就是 block，会整屏盖住书库列表（桌面端是 static 所以不明显）。
   放在所有媒体查询之外并加 !important，确保任何视口下行为一致。 */
.br-settings-view:not(.open),
.br-portal-offline-reader:not(.open) { display: none !important; }
.br-settings-view.open,
.br-portal-offline-reader.open { display: block !important; }

@media (min-width: 769px) {
    /* 宽屏（含从手机尺寸切回桌面尺寸）：隐藏底部导航与未打开的全屏层。
       上面所有 bottom 上移规则都包在 max-width:768px 内，此处不生效，
       #brLockFab / #brEditFab / .progress-info 等自动恢复各自原始的
       bottom:16px / 72px / 10px，无需 JS 干预。 */
    .br-mobile-nav,
    .br-settings-view:not(.open),
    .br-portal-offline-reader:not(.open) { display: none !important; }

    /* 宽屏用书库页顶部的按钮打开同一个独立设置页；打开时是全屏层而不是
       追加在书库下方的一段内容，避免设置页把书库挤走。 */
    .br-portal-settings-btn { display: inline-flex; }
    .br-settings-view.open,
    .br-portal-offline-reader.open {
        position: fixed; inset: 0; overflow-y: auto; display: block !important;
        background: var(--br-page-bg, #fafafa); color: var(--br-page-fg, #222);
    }
    .br-settings-view.open { z-index: 4000; }
    .br-portal-offline-reader.open {
        z-index: 4500;
        background: var(--reader-bg, var(--br-page-bg, #fff));
        color: var(--reader-text, var(--br-page-fg, #222));
    }
    .br-settings-view.open .br-settings-head {
        position: sticky; top: 0; z-index: 2; display: flex; align-items: center; gap: 12px;
        padding: 12px 16px; background: var(--br-card-bg, #fff);
        border-bottom: 1px solid var(--br-nav-border, #e2e4e8);
    }
    .br-settings-view.open .br-settings-head h2 { margin: 0; font-size: 18px; flex: 1; }
    .br-settings-view.open .br-settings-head button { min-width: 44px; min-height: 44px; border: 0; background: transparent; color: inherit; font-size: 16px; }
    .br-settings-view.open .br-settings-group { max-width: 720px; margin: 16px auto; padding: 14px; border-radius: 12px; background: var(--br-card-bg, #fff); }
    .br-settings-view.open .br-setting-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 48px; }
    .br-settings-view.open .br-setting-row input[type=text],
    .br-settings-view.open .br-setting-row input[type=password] {
        flex: 1 1 200px; min-height: 40px; padding: 6px 10px; border-radius: 8px;
        border: 1px solid var(--br-nav-border, #ddd); background: var(--br-card-bg, #fff); color: inherit;
    }
    .br-settings-view.open .br-setting-actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .br-settings-view.open .br-setting-actions button {
        min-height: 44px; padding: 0 14px; border-radius: 10px;
        border: 1px solid var(--br-nav-border, #ddd); background: var(--br-card-bg, #fff); color: inherit;
    }
    .br-portal-offline-reader.open .br-offline-body { max-width: 820px; margin: 0 auto; padding: 20px 16px 100px; line-height: 1.8; word-wrap: break-word; }
}
"""

# --------------------------------------------------------------------------- #
# 2. 手机端底部导航 + 独立设置页 DOM（注入到阅读器页面）
# --------------------------------------------------------------------------- #
MOBILE_HTML = r"""
<nav class="br-mobile-nav" id="brMobileNav" aria-label="移动端导航">
    <button type="button" data-br-nav="read" class="active"><span class="br-nav-icon">&#128214;</span><span data-br-label="read">阅读</span></button>
    <button type="button" data-br-nav="toc"><span class="br-nav-icon">&#9776;</span><span data-br-label="toc">目录</span></button>
    <button type="button" data-br-nav="search"><span class="br-nav-icon">&#128269;</span><span data-br-label="search">搜索</span></button>
    <button type="button" data-br-nav="library"><span class="br-nav-icon">&#128218;</span><span data-br-label="library">书库</span></button>
    <button type="button" data-br-nav="settings"><span class="br-nav-icon">&#9881;</span><span data-br-label="settings">设置</span></button>
</nav>

<section class="br-settings-view" id="brSettingsView" aria-label="设置">
    <div class="br-settings-head">
        <button type="button" id="brSettingsBack" aria-label="返回">&#8592;</button>
        <h2 data-br-label="settings">设置</h2>
        <span class="br-net-badge offline" id="brSettingsNet">离线</span>
    </div>

    <div class="br-settings-group">
        <h3 data-br-label="appearance">外观</h3>
        <div class="br-setting-row">
            <label for="brSetTheme" data-br-label="theme">主题</label>
            <select id="brSetTheme"></select>
        </div>
        <div class="br-setting-row">
            <label for="brSetFontSize" data-br-label="font_size">字号</label>
            <input type="range" id="brSetFontSize" min="12" max="32" step="1" value="18">
            <span class="br-value" id="brSetFontSizeValue">18</span>
        </div>
        <div class="br-setting-row">
            <label for="brSetLineHeight" data-br-label="line_height">行高</label>
            <input type="range" id="brSetLineHeight" min="12" max="28" step="1" value="18">
            <span class="br-value" id="brSetLineHeightValue">1.8</span>
        </div>
        <div class="br-setting-row">
            <label for="brSetWidth" data-br-label="page_width">页面宽度</label>
            <input type="range" id="brSetWidth" min="60" max="100" step="1" value="100">
            <span class="br-value" id="brSetWidthValue">100%</span>
        </div>
        <div class="br-setting-actions">
            <button type="button" id="brSetNight" data-br-label="night_mode">夜间模式</button>
            <button type="button" id="brSetFullWidth" data-br-label="full_width">宽屏阅读</button>
            <button type="button" id="brSetFocus" data-br-label="focus_mode">专注模式</button>
            <button type="button" id="brSetFontPanel" data-br-label="font_settings">字体设置</button>
        </div>
    </div>

    <div class="br-settings-group">
        <h3 data-br-label="reading">阅读</h3>
        <div class="br-setting-actions">
            <button type="button" id="brSetToc" data-br-label="toc">章节目录</button>
            <button type="button" id="brSetBookmarks" data-br-label="bookmarks">书签 / 笔记</button>
            <button type="button" id="brSetPagination" data-br-label="pagination">翻页设置</button>
            <button type="button" id="brSetPosition" data-br-label="jump">位置跳转</button>
            <button type="button" id="brSetAutoScroll" data-br-label="auto_scroll">自动滚动</button>
            <button type="button" id="brSetSpeech" data-br-label="speech">朗读</button>
            <button type="button" id="brSetDownload" data-br-label="download_txt" hidden>下载 TXT</button>
        </div>
    </div>

    <div class="br-settings-group">
        <h3 data-br-label="network">连接与同步</h3>
        <div class="br-setting-row">
            <label for="brSetBackend" data-br-label="backend">后端地址</label>
            <input type="text" id="brSetBackend" placeholder="http://192.168.1.10:54321" autocomplete="off">
        </div>
        <div class="br-setting-row">
            <label for="brSetSecret" data-br-label="api_key">接口密钥</label>
            <input type="password" id="brSetSecret" placeholder="" autocomplete="off">
        </div>
        <div class="br-setting-row">
            <label data-br-label="status">状态</label>
            <span class="br-net-badge offline" id="brNetBadge">离线</span>
        </div>
        <div class="br-setting-actions">
            <button type="button" class="primary" id="brSetSaveConn" data-br-label="save">保存并检测</button>
            <button type="button" id="brSetSync" data-br-label="sync_now">立即同步</button>
            <button type="button" id="brSetPortal" data-br-label="book_library">返回书库</button>
        </div>
        <p style="font-size:12px;opacity:.65;margin:10px 0 0" data-br-label="offline_hint">
            后端关闭后仍可继续阅读：正文已保存在本机，进度暂存本地，恢复连接后自动同步。
        </p>
    </div>
</section>
"""

# --------------------------------------------------------------------------- #
# 3. 注入阅读器页面的 JS
# --------------------------------------------------------------------------- #
# 说明：脚本在主 <script> 之后同步执行，顶层 let 变量（SAVE_PROGRESS_URL 等）
# 位于全局词法环境，可直接赋值；DOMContentLoaded 尚未触发，因此健康检查会用新地址。
READER_WEB_JS = r"""
(function () {
    'use strict';
    var LABELS = __BR_LABELS__;
    var API_KEY_STORAGE = 'br_api_secret';
    var BACKEND_STORAGE = 'br_backend_override';
    var CACHE_DB = 'br_offline_books';
    var CACHE_STORE = 'books';

    function $(id) { return document.getElementById(id); }
    function safe(fn) { try { return fn(); } catch (e) { return null; } }
    function isHttp() { return location.protocol === 'http:' || location.protocol === 'https:'; }
    function compact() { return window.innerWidth <= 768; }

    /* ---------- 后端地址：HTTP 页面用 location.origin，file:// 用注入值 ---------- */
    function resolveBackend() {
        var override = safe(function () { return localStorage.getItem(BACKEND_STORAGE); });
        var base = override || (isHttp() ? location.origin : '');
        if (!base) { return null; }
        base = base.replace(/\/+$/, '');
        safe(function () {
            /* 主脚本的 let 变量位于全局词法环境，后续 script 可直接改写 */
            SAVE_PROGRESS_URL = base + '/save_progress';
            LOAD_PROGRESS_URL = base + '/load_progress';
            window.SAVE_PROGRESS_URL = SAVE_PROGRESS_URL;
            window.LOAD_PROGRESS_URL = LOAD_PROGRESS_URL;
            window.__BR_API_BASE__ = base;
        });
        return base;
    }
    var BACKEND = resolveBackend();

    function currentKey() {
        return safe(function () { return localStorage.getItem(API_KEY_STORAGE); }) || (typeof READER_SECRET !== 'undefined' ? READER_SECRET : '') || '';
    }
    function withKey(url) {
        var k = currentKey();
        if (!k) { return url; }
        return url + (url.indexOf('?') >= 0 ? '&' : '?') + 'key=' + encodeURIComponent(k);
    }

    /* ---------- 屏宽分类：驱动 CSS 与设置页显隐 ---------- */
    function syncViewportClass() {
        var root = document.documentElement;
        root.classList.toggle('br-compact', compact());
        root.classList.toggle('br-dark', safe(function () {
            return document.body && (document.body.classList.contains('dark-mode') || document.body.classList.contains('night-mode'));
        }) || false);
        if (!compact()) { closeSettings(); }
    }

    /* ---------- 在线 / 离线状态（同一页面内自动切换） ---------- */
    var netOnline = false;
    function paintNet() {
        var text = netOnline ? LABELS.online : LABELS.offline;
        ['brNetBadge', 'brSettingsNet'].forEach(function (id) {
            var el = $(id);
            if (!el) { return; }
            el.textContent = text;
            el.className = 'br-net-badge ' + (netOnline ? 'online' : 'offline');
        });
    }
    function checkNet() {
        if (!BACKEND) { netOnline = false; paintNet(); return; }
        var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
        var timer = setTimeout(function () { if (ctrl) { ctrl.abort(); } }, 2500);
        fetch(BACKEND + '/health_check', ctrl ? { signal: ctrl.signal, cache: 'no-store' } : { cache: 'no-store' })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) { netOnline = !!(d && d.status === 'ok'); })
            .catch(function () { netOnline = false; })
            .finally(function () { clearTimeout(timer); paintNet(); });
    }

    /* ---------- 正文缓存到 IndexedDB（后端彻底关闭也能重开阅读） ---------- */
    function openCacheDB() {
        return new Promise(function (resolve, reject) {
            if (!window.indexedDB) { reject(new Error('no-idb')); return; }
            var req = indexedDB.open(CACHE_DB, 1);
            req.onupgradeneeded = function () {
                var db = req.result;
                if (!db.objectStoreNames.contains(CACHE_STORE)) { db.createObjectStore(CACHE_STORE, { keyPath: 'id' }); }
            };
            req.onsuccess = function () { resolve(req.result); };
            req.onerror = function () { reject(req.error); };
        });
    }
    /* 标题伪装（老板键 / 切标签）会把 document.title 改成“百度一下，你就知道”。
       beforeunload 时若两个监听器顺序不利，cacheCurrentBook 会把这个伪装标题当作书名
       持久化到 IndexedDB，导致本地书面板标题显示成“百度一下”。书名只从不受伪装影响的
       __BR_BOOK_ID__ / data-original-title 读取，绝不直接用 document.title。 */
    function stableBookTitle() {
        var t = '';
        try {
            /* __BR_BOOK_ID__ 是生成页面时写入的真实书名，不受任何标题伪装影响 */
            t = String(window.__BR_BOOK_ID__ || '');
            if (!t) {
                var el = document.querySelector('[data-original-title]');
                if (el) { t = el.getAttribute('data-original-title') || ''; }
            }
            if (!t) { t = String(window.__BR_BOOK_TITLE__ || ''); }
        } catch (e) {}
        t = String(t || '').replace(/\s*-\s*(浏览器阅读器|Browser Reader)\s*$/i, '').trim();
        /* 兜底：任何含“百度”伪装特征的标题都视为无效，退回可读占位 */
        if (!t || /百度一下|百度一下[,，]你就知道/.test(t)) { t = 'book'; }
        return t;
    }
    function cacheCurrentBook() {
        var el = $('content');
        if (!el || !el.innerHTML) { return; }
        var legacyId = safe(function () { return window.__BR_BOOK_ID__; }) || document.title || 'book';
        var bookKey = safe(function () {
            return window.__BR_BOOK_KEY__ || window.__BR_ACTIVE_BOOK_KEY__ || '';
        }) || '';
        try {
            if (!bookKey) { bookKey = new URLSearchParams(location.search).get('book') || ''; }
        } catch (e) {}
        /* 旧版阅读页可能只注入 path 而没有合法 book key：若把书名当 key 缓存，
           书库会拼出 /reader?book=<书名> 并被后端 404。宁可留空，按本地正文打开。 */
        if (!/^[0-9a-f]{20}$/i.test(String(bookKey).trim())) { bookKey = ''; }
        /* 新缓存用不可逆的 book key 作主键；旧缓存仍按 book_id / path 兼容读取。 */
        var id = bookKey || legacyId;
        var bookTitle = stableBookTitle();
        openCacheDB().then(function (db) {
            var tx = db.transaction(CACHE_STORE, 'readwrite');
            tx.objectStore(CACHE_STORE).put({
                id: String(id), book_key: String(bookKey), book_id: String(legacyId),
                title: bookTitle,
                html: el.innerHTML,
                path: safe(function () { return window.__BR_BOOK_FILE_PATH__; }) || '',
                savedAt: Date.now()
            });
            tx.oncomplete = function () { db.close(); };
        }).catch(function () {});
    }

    /* ---------- Service Worker：让 HTTP 页面在后端关闭后仍可打开 ---------- */
    function registerSW() {
        if (!isHttp() || !('serviceWorker' in navigator)) { return; }
        navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
    }

    /* ---------- 手机端独立设置页 ---------- */
    function openSettings() {
        var v = $('brSettingsView');
        if (v) { v.classList.add('open'); }
        location.hash = 'settings';
        syncSettingsForm();
        checkNet();
    }
    function closeSettings() {
        var v = $('brSettingsView');
        if (v) { v.classList.remove('open'); }
        if (location.hash === '#settings') {
            /* file:// 页面部分浏览器禁止 replaceState，失败时仅保留 hash，不影响阅读 */
            safe(function () { history.replaceState(null, '', location.pathname + location.search + '#read'); });
        }
    }
    function callGlobal(name, arg) {
        return safe(function () {
            /* 主脚本的函数声明位于全局对象上，直接取用即可，无需 eval */
            var fn = window[name];
            if (typeof fn === 'function') { fn(arg); return true; }
            return false;
        });
    }

    function currentSettingsObj() {
        return safe(function () { return currentSettings; }) || {};
    }
    function syncSettingsForm() {
        var s = currentSettingsObj();
        var themeSel = $('brSetTheme');
        if (themeSel && !themeSel.options.length) {
            var names = safe(function () { return Object.keys(themes || {}); }) || ['light', 'dark', 'sepia'];
            names.forEach(function (n) {
                var o = document.createElement('option'); o.value = n; o.textContent = n; themeSel.appendChild(o);
            });
        }
        if (themeSel && s.theme) { themeSel.value = s.theme; }
        var size = parseInt(s.font_size || 18, 10);
        var lh = parseFloat(s.line_height || 1.8);
        if ($('brSetFontSize')) { $('brSetFontSize').value = size; $('brSetFontSizeValue').textContent = String(size); }
        if ($('brSetLineHeight')) { $('brSetLineHeight').value = Math.round(lh * 10); $('brSetLineHeightValue').textContent = lh.toFixed(1); }
        if ($('brSetWidth')) { $('brSetWidth').value = parseInt(s.width_pct || 100, 10); $('brSetWidthValue').textContent = (s.width_pct || 100) + '%'; }
        if ($('brSetBackend')) { $('brSetBackend').value = BACKEND || ''; }
        if ($('brSetSecret')) { $('brSetSecret').value = currentKey(); }
    }
    function updateSetting(key, value) {
        safe(function () {
            if (typeof currentSettings === 'undefined') { return; }
            currentSettings[key] = value;
            if (typeof saveSettings === 'function') { saveSettings(); }
            if (typeof applySettings === 'function') { applySettings(currentSettings); }
        });
    }

    function bindSettings() {
        var back = $('brSettingsBack');
        if (back) { back.addEventListener('click', closeSettings); }

        var themeSel = $('brSetTheme');
        if (themeSel) {
            themeSel.addEventListener('change', function () {
                if (!callGlobal('changeTheme', themeSel.value)) { updateSetting('theme', themeSel.value); }
            });
        }
        var fs = $('brSetFontSize');
        if (fs) {
            fs.addEventListener('input', function () {
                $('brSetFontSizeValue').textContent = fs.value;
                /* updateSetting 已经调用 applySettings（内含翻页样式刷新）。
                   不要再调 changeFontSize(0)：它用 getComputedStyle 反推字号并
                   写回 currentSettings，字号被 CSS 锁定或浏览器做字体缩放时会
                   把刚设置的新值改回旧值。 */
                updateSetting('font_size', fs.value);
            });
        }
        var lh = $('brSetLineHeight');
        if (lh) {
            lh.addEventListener('input', function () {
                var v = (parseInt(lh.value, 10) / 10).toFixed(1);
                $('brSetLineHeightValue').textContent = v;
                updateSetting('line_height', v);
            });
        }
        var wd = $('brSetWidth');
        if (wd) {
            wd.addEventListener('input', function () {
                $('brSetWidthValue').textContent = wd.value + '%';
                updateSetting('width_pct', wd.value);
                safe(function () { document.body.style.maxWidth = wd.value + '%'; });
            });
        }
        var actions = {
            brSetNight: 'toggleNightMode', brSetFullWidth: 'toggleFullWidthReading',
            brSetFocus: 'toggleFocusMode', brSetFontPanel: 'toggleFontSettings',
            brSetToc: 'toggleTOC', brSetBookmarks: 'toggleNotesMode',
            brSetPagination: 'togglePaginationSettings', brSetPosition: 'togglePositionJump',
            brSetAutoScroll: 'toggleAutoScrollPanel', brSetSpeech: 'toggleSpeech',
            brSetSync: 'manualSync'
        };
        Object.keys(actions).forEach(function (id) {
            var btn = $(id);
            if (btn) { btn.addEventListener('click', function () { closeSettings(); callGlobal(actions[id]); }); }
        });
        /* 下载入口只在局域网阅读页出现（file:// 离线版没有 /download_book 服务） */
        var downloadBtn = $('brSetDownload');
        if (downloadBtn) {
            if (safe(function () { return window.__BR_LAN_DOWNLOAD__; })) { downloadBtn.hidden = false; }
            downloadBtn.addEventListener('click', function () { closeSettings(); callGlobal('downloadBookAsTxt'); });
        }
        var portal = $('brSetPortal');
        if (portal) { portal.addEventListener('click', function () { if (isHttp()) { location.href = withKey('/'); } }); }
        var saveConn = $('brSetSaveConn');
        if (saveConn) {
            saveConn.addEventListener('click', function () {
                var url = ($('brSetBackend').value || '').trim().replace(/\/+$/, '');
                safe(function () {
                    if (url) { localStorage.setItem(BACKEND_STORAGE, url); } else { localStorage.removeItem(BACKEND_STORAGE); }
                    localStorage.setItem(API_KEY_STORAGE, $('brSetSecret').value || '');
                });
                BACKEND = resolveBackend();
                checkNet();
            });
        }
    }

    function bindNav() {
        var nav = $('brMobileNav');
        if (!nav) { return; }
        nav.addEventListener('click', function (e) {
            var btn = e.target.closest ? e.target.closest('button[data-br-nav]') : null;
            if (!btn) { return; }
            var which = btn.getAttribute('data-br-nav');
            Array.prototype.forEach.call(nav.querySelectorAll('button'), function (b) { b.classList.remove('active'); });
            if (which !== 'settings') { btn.classList.add('active'); }
            closeSettings();
            if (which === 'settings') { openSettings(); return; }
            if (which === 'toc') { callGlobal('toggleTOC'); }
            else if (which === 'search') { callGlobal('toggleSearch'); }
            else if (which === 'library') {
                /* 局域网页面有专门的移动端书库入口；file:// 页面回退到页内书库弹窗 */
                if (isHttp()) { location.href = withKey('/'); }
                else { callGlobal('toggleBookLibrary'); }
            }
            else { safe(function () { window.scrollTo(0, 0); }); }
        });
    }

    function applyLabels() {
        Array.prototype.forEach.call(document.querySelectorAll('[data-br-label]'), function (el) {
            var k = el.getAttribute('data-br-label');
            if (LABELS[k]) { el.textContent = LABELS[k]; }
        });
    }

    function init() {
        document.body.classList.add('br-web');
        applyLabels();
        syncViewportClass();
        bindNav();
        bindSettings();
        paintNet();
        checkNet();
        setInterval(checkNet, 30000);
        window.addEventListener('resize', syncViewportClass);
        window.addEventListener('hashchange', function () {
            if (location.hash === '#settings') { openSettings(); } else { closeSettings(); }
        });
        if (location.hash === '#settings') { openSettings(); }
        setTimeout(cacheCurrentBook, 1200);
        window.addEventListener('beforeunload', cacheCurrentBook);
        registerSW();
        window.__BR_WEB__ = { backend: BACKEND, checkNet: checkNet, openSettings: openSettings, cacheCurrentBook: cacheCurrentBook };
    }

    if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); } else { init(); }
})();
"""

# --------------------------------------------------------------------------- #
# 4. Service Worker
# --------------------------------------------------------------------------- #
# 缓存策略：
#  - 导航请求（/、/reader?...）：网络优先，失败回退缓存；保证后端在线时拿到最新，
#    后端关闭后依然能打开已访问过的页面。
#  - /sw.js、/health_check 等不缓存，避免把「离线」误判成「在线」。
SERVICE_WORKER_JS = r"""
const CACHE = 'br-reader-v66';
/* ---- 旧缓存页面迁移 ----
   早期窄屏 CSS 把正文字号写成 `font-size: 17px !important`，且设置页滑块还会再调
   `changeFontSize(0)`（按 getComputedStyle 反推字号，配合 body 的 transition 会把
   刚设的字号写回旧值）。后端关闭时导航请求回退到缓存的旧 HTML，前端修复送不到
   这些页面。SW 更新（activate）时把这两处精确剔除并回写，离线打开的旧页面也
   随之恢复；离线回退时再做一次兜底。缓存名保持不变，避免删掉离线书籍。 */
const LEGACY_FONT_LOCK = /font-size\s*:\s*17px\s*!important\s*;\s*line-height\s*:\s*1\.8\s*!important\s*;/g;
const LEGACY_FONT_JS = /callGlobal\('changeFontSize',\s*0\);/g;
function stripLegacyFontLock(res) {
    if (!res || (res.headers.get('Content-Type') || '').indexOf('text/html') < 0) {
        return Promise.resolve(res);
    }
    return res.clone().text().then(function (text) {
        var fixed = text.replace(LEGACY_FONT_LOCK, '').replace(LEGACY_FONT_JS, '');
        if (fixed === text) { return res; }
        return new Response(fixed, {
            status: res.status, statusText: res.statusText,
            headers: { 'Content-Type': 'text/html; charset=utf-8' }
        });
    }).catch(function () { return res; });
}
function patchCachedPages() {
    return caches.open(CACHE).then(function (c) {
        return c.keys().then(function (keys) {
            return Promise.all(keys.map(function (req) {
                return c.match(req).then(function (res) {
                    if (!res) { return; }
                    return stripLegacyFontLock(res).then(function (fixed) {
                        if (fixed !== res) { return c.put(req, fixed); }
                    });
                });
            }));
        });
    }).catch(function () {});
}
/* 缓存键去掉 ?key=（密钥变化不应导致缓存失效），但保留 /reader 的书籍标识（每本书独立缓存）。
   新链接用 ?book=<公开标识>，旧链接 ?path=<物理路径> 仍可缓存，避免老书签失效。 */
function cacheKey(raw) {
    var u = new URL(raw);
    var k = u.origin + u.pathname;
    if (u.pathname === '/reader') {
        var id = u.searchParams.get('book') || u.searchParams.get('path') || '';
        k += '?id=' + encodeURIComponent(id);
    }
    return k;
}
/* gzip 响应在 fetch() 后已被浏览器解码，缓存时去掉 Content-Encoding/Length，
   避免离线命中缓存时再次按 gzip 解码导致乱码。 */
function cacheableResponse(res) {
    var headers = new Headers(res.headers);
    headers.delete('Content-Encoding');
    headers.delete('Content-Length');
    return res.clone().text().then(function (text) {
        return new Response(text, {
            status: res.status, statusText: res.statusText, headers: headers
        });
    });
}
/* 不做 install 预缓存：配置了接口密钥时匿名请求 '/' 会拿到 401 页面并污染缓存 */
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
    e.waitUntil(caches.keys().then(function (keys) {
        return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    }).then(patchCachedPages).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
    var req = e.request;
    if (req.method !== 'GET') { return; }
    var url = new URL(req.url);
    if (url.origin !== self.location.origin) { return; }
    if (url.pathname === '/sw.js' || url.pathname === '/health_check' || url.pathname === '/manifest.webmanifest') { return; }
    /* 书籍下载必须每次回源，不能被离线缓存污染 */
    if (url.pathname === '/download_book') { return; }
    if (url.pathname.indexOf('/api/') === 0) { return; }

    if (req.mode === 'navigate' || url.pathname === '/' || url.pathname === '/reader') {
        var key = cacheKey(req.url);
        e.respondWith(
            fetch(req).then(function (res) {
                if (res && res.ok) {
                    cacheableResponse(res).then(function (copy) {
                        return caches.open(CACHE).then(function (c) { return c.put(key, copy); });
                    }).catch(function () {});
                }
                return res;
            }).catch(function () {
                return caches.match(key).then(function (hit) {
                    if (hit) { return stripLegacyFontLock(hit); }
                    return caches.match(new URL('/', self.location.origin).href).then(stripLegacyFontLock);
                }).then(function (res) {
                    return res || new Response(
                        '<!doctype html><meta charset="utf-8"><p style="font:16px/1.8 sans-serif;padding:24px">后端未运行，且本机没有该页面的离线缓存。可在书库页「离线」中打开已缓存的书籍。</p>',
                        { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
                    );
                });
            })
        );
        return;
    }
    e.respondWith(caches.match(req).then(function (hit) { return hit || fetch(req); }));
});
"""

# --------------------------------------------------------------------------- #
# 5. 文案（前端内联，避免新增后端翻译接口）
# --------------------------------------------------------------------------- #
LABELS: Dict[str, Dict[str, str]] = {
    "zh_CN": {
        "read": "阅读", "toc": "目录", "search": "搜索", "library": "书库", "settings": "设置",
        "appearance": "外观", "reading": "阅读", "network": "连接与同步",
        "theme": "主题", "font_size": "字号", "line_height": "行高", "page_width": "页面宽度",
        "night_mode": "夜间模式", "full_width": "宽屏阅读", "focus_mode": "专注模式",
        "font_settings": "字体设置", "bookmarks": "书签 / 笔记", "pagination": "翻页设置",
        "jump": "位置跳转", "auto_scroll": "自动滚动", "speech": "朗读",
        "backend": "后端地址", "api_key": "接口密钥", "status": "状态",
        "save": "保存并检测", "sync_now": "立即同步", "book_library": "返回书库",
        "download_txt": "下载 TXT", "downloading": "正在生成 TXT…",
        "download_done": "TXT 已开始下载", "download_failed": "下载失败",
        "offline_hint": "后端关闭后仍可继续阅读：正文已保存在本机，进度暂存本地，恢复连接后自动同步。",
        "online": "在线", "offline": "离线",
        "portal_title": "书库", "portal_search": "搜索书名 / 作者",
        "portal_tagline": "随时读，随身带", "portal_count": "共 %d 本", "portal_found": "找到 %d 本",
        "portal_page": "第 %d / %d 页", "portal_page_label": "分页",
        "portal_prev": "上一页", "portal_next": "下一页",
        "portal_refresh": "刷新", "portal_upload": "上传书籍", "portal_empty": "暂无书籍", "portal_no_match": "没有找到匹配的书籍",
        "portal_history": "阅读历史", "portal_local_books": "本地书籍", "portal_network_books": "网络书籍",
        "sync_to_backend": "同步到后端", "synced": "已同步", "history_empty": "暂无阅读历史", "local_empty": "本地书库暂无书籍",
        "upload_ok": "上传成功", "upload_failed": "上传失败", "offline_upload_text_only": "离线版目前仅支持上传 TXT/MD 文本文件",
        "binary_local_hint": "该格式暂不支持浏览器内直接阅读，请先同步到后端。",
        "portal_offline_books": "离线书籍", "portal_online_books": "书库",
        "portal_offline_tip": "后端已关闭，显示本机缓存", "portal_online_tip": "已连接后端",
        "portal_no_offline": "还没有离线缓存的书籍，请在线打开一次",
        "portal_settings": "设置", "portal_back": "返回",
        "portal_clear_cache": "清除离线缓存", "portal_cleared": "已清除",
        "portal_open_failed": "打开失败，请检查后端与密钥",
        "portal_loading": "正在打开书籍",
        "portal_confirm_delete_history": "确定删除选中的阅读历史？",
        "portal_confirm_clear_history": "确定清除全部阅读历史？此操作不可恢复。",
        "portal_manage_local": "管理", "portal_select_all": "全选", "portal_delete_selected": "删除选中",
        "portal_delete_all": "全部清除", "portal_cancel": "取消", "portal_select_first": "请先选择书籍",
        "portal_confirm_delete_selected": "确定删除选中的书籍？此操作不可恢复。",
        "portal_confirm_delete_all": "确定清除全部本地书籍？此操作不可恢复。",
    },
    "en_US": {
        "read": "Read", "toc": "Contents", "search": "Search", "library": "Library", "settings": "Settings",
        "appearance": "Appearance", "reading": "Reading", "network": "Connection & Sync",
        "theme": "Theme", "font_size": "Font size", "line_height": "Line height", "page_width": "Page width",
        "night_mode": "Night mode", "full_width": "Full width", "focus_mode": "Focus mode",
        "font_settings": "Font settings", "bookmarks": "Bookmarks / Notes", "pagination": "Page turn",
        "jump": "Jump to position", "auto_scroll": "Auto scroll", "speech": "Read aloud",
        "backend": "Backend URL", "api_key": "API key", "status": "Status",
        "save": "Save & check", "sync_now": "Sync now", "book_library": "Back to library",
        "download_txt": "Download TXT", "downloading": "Preparing TXT…",
        "download_done": "TXT download started", "download_failed": "Download failed",
        "offline_hint": "You can keep reading when the backend is down: content is cached on this device and progress is stored locally until the connection returns.",
        "online": "Online", "offline": "Offline",
        "portal_title": "Library", "portal_search": "Search title / author",
        "portal_tagline": "Books, anywhere", "portal_count": "%d books", "portal_found": "%d found",
        "portal_page": "Page %d / %d", "portal_page_label": "Pagination",
        "portal_prev": "Previous page", "portal_next": "Next page",
        "portal_refresh": "Refresh", "portal_upload": "Upload", "portal_empty": "No books", "portal_no_match": "No matching books",
        "portal_history": "History", "portal_local_books": "Local", "portal_network_books": "Network",
        "sync_to_backend": "Sync to server", "synced": "Synced", "history_empty": "No reading history", "local_empty": "No local books",
        "upload_ok": "Uploaded", "upload_failed": "Upload failed", "offline_upload_text_only": "Offline mode supports TXT/MD text files only",
        "binary_local_hint": "This format cannot be read directly in the browser yet. Please sync it to the server first.",
        "portal_offline_books": "Offline", "portal_online_books": "Library",
        "portal_offline_tip": "Backend offline, showing local cache", "portal_online_tip": "Connected to backend",
        "portal_no_offline": "No cached books yet — open one while online",
        "portal_settings": "Settings", "portal_back": "Back",
        "portal_clear_cache": "Clear offline cache", "portal_cleared": "Cleared",
        "portal_open_failed": "Failed to open, check backend and API key",
        "portal_loading": "Opening book",
        "portal_confirm_delete_history": "Delete selected reading history?",
        "portal_confirm_clear_history": "Clear all reading history? This cannot be undone.",
        "portal_manage_local": "Manage", "portal_select_all": "Select all", "portal_delete_selected": "Delete selected",
        "portal_delete_all": "Clear all", "portal_cancel": "Cancel", "portal_select_first": "Select books first",
        "portal_confirm_delete_selected": "Delete selected books? This cannot be undone.",
        "portal_confirm_delete_all": "Clear all local books? This cannot be undone.",
    },
}


def _js_json(value: Any) -> str:
    """生成可安全内嵌到 <script> 的 JSON 字面量。

    转义 ``<`` / ``>`` / ``&``，避免密钥或文案里出现 ``</script>`` 时截断脚本。
    """
    return (json.dumps(value, ensure_ascii=False)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026"))


def get_labels(locale: Optional[str] = None) -> Dict[str, str]:
    """返回指定语言的前端文案（未知语言回退中文）。"""
    try:
        if not locale:
            from src.locales.i18n_manager import get_global_i18n
            locale = get_global_i18n().current_locale
    except Exception:
        locale = "zh_CN"
    return LABELS.get(locale or "zh_CN", LABELS["zh_CN"])


def render_reader_web_js(locale: Optional[str] = None) -> str:
    """把文案注入阅读器 Web JS。"""
    return READER_WEB_JS.replace("__BR_LABELS__", _js_json(get_labels(locale)))


# --------------------------------------------------------------------------- #
# 浏览器阅读器「开屏密码」门禁（离线 file:// 页 / 局域网书库入口页共用）
# --------------------------------------------------------------------------- #
# 密码在「平台设置中心」设置，后端只把 SHA-256 摘要注入页面，页面内不含明文；
# 校验完全在前端完成，因此离线版与局域网版行为一致，且不依赖 crypto.subtle
# （局域网 http:// 并非安全上下文，crypto.subtle 不可用，故自带纯 JS SHA-256）。
def startup_password_hash(password: str) -> str:
    """返回开屏密码的 SHA-256 十六进制摘要，用于注入页面做前端校验。

    未设置密码时返回空串：页面据此提示「尚未在设置中心设置开屏密码」，
    避免用空串摘要把用户挡在门外却给出「密码错误」的误导信息。
    """
    import hashlib
    pwd = password or ""
    if not pwd:
        return ""
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


def render_startup_gate_early_js(enabled: bool, password_hash: str = "") -> str:
    """生成放在 <head> 中最先执行的脚本：注入开关/摘要并立即隐藏正文，避免闪现。"""
    return (
        '<script>\n'
        '(function(){\n'
        '  try {\n'
        '    window.__BR_STARTUP_PASSWORD_ENABLED__ = ' + ('true' if enabled else 'false') + ';\n'
        '    window.__BR_STARTUP_PASSWORD_HASH__ = ' + _js_json(password_hash or "") + ';\n'
        '    function brUnlockedHash(){ var exp=window.__BR_STARTUP_PASSWORD_HASH__||""; if(!exp) return false;\n'
        '      try { var parts=document.cookie.split(";"), name="br_startup_unlocked_hash="; for(var i=0;i<parts.length;i++){ var p=parts[i].trim(); if(p.indexOf(name)===0 && decodeURIComponent(p.slice(name.length))===exp) return true; } } catch(e){}\n'
        '      try { if (localStorage.getItem("br_startup_unlocked_hash")===exp) return true; } catch(e){}\n'
        '      return false; }\n'
        '    var unlocked = brUnlockedHash();\n'
        '    if (window.__BR_STARTUP_PASSWORD_ENABLED__ && !unlocked) {\n'
        '      document.documentElement.classList.add("br-startup-locked");\n'
        '    }\n'
        '  } catch(e) {}\n'
        '})();\n'
        '</script>\n'
    )


STARTUP_GATE_CSS = r"""
/* === 浏览器阅读器开屏密码门禁 === */
html.br-startup-locked, html.br-startup-locked body { overflow: hidden !important; }
html.br-startup-locked #content,
html.br-startup-locked #portalRoot,
html.br-startup-locked .br-portal { visibility: hidden !important; }
html.br-startup-locked #brLockFab,
html.br-startup-locked #brEditFab,
html.br-startup-locked .br-sync-badge { display: none !important; }
#brStartupGate {
  position: fixed; inset: 0; z-index: 2147483647 !important; display: none;
  align-items: center; justify-content: center;
  background: #0d0f14; color: #e8eaf0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
html.br-startup-locked #brStartupGate { display: flex !important; }
#brStartupGate .br-startup-card {
  width: 90%; max-width: 380px; display: flex; flex-direction: column; align-items: center; gap: 14px;
}
#brStartupGate .br-startup-icon { font-size: 44px; line-height: 1; }
#brStartupGate .br-startup-title { font-size: 19px; font-weight: 600; }
#brStartupGate .br-startup-hint { font-size: 13px; opacity: 0.6; text-align: center; line-height: 1.7; }
#brStartupGate .br-pwd-row { position: relative; display: flex; align-items: center; width: 100%; }
#brStartupGate input.br-startup-pwd {
  width: 100%; box-sizing: border-box; padding: 12px 44px 12px 16px; font-size: 16px;
  border-radius: 10px; border: 1px solid #2a2f3a; background: #161a22; color: #e8eaf0;
  outline: none; text-align: center; font-family: inherit;
}
#brStartupGate input.br-startup-pwd:focus { border-color: #4facfe; }
#brStartupGate .br-startup-eye {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  display: flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; padding: 0; border: none; background: transparent;
  color: #8a93a6; cursor: pointer; border-radius: 8px;
}
#brStartupGate .br-startup-eye:hover { color: #4facfe; background: rgba(255,255,255,0.06); }
#brStartupGate .br-startup-eye svg { display: block; }
#brStartupGate .br-startup-eye .br-startup-eye-off { display: none; }
#brStartupGate .br-startup-eye.br-startup-eye-on .br-startup-eye-open { display: none; }
#brStartupGate .br-startup-eye.br-startup-eye-on .br-startup-eye-off { display: block; }
#brStartupGate .br-startup-btn {
  width: 100%; padding: 12px; font-size: 16px; border: none; border-radius: 10px;
  cursor: pointer; background: #4facfe; color: #fff; font-weight: 600; font-family: inherit;
}
#brStartupGate .br-startup-btn:hover { background: #3a9fe8; }
#brStartupGate .br-startup-msg { font-size: 13px; min-height: 18px; color: #ff6b6b; }
"""

STARTUP_GATE_HTML = r"""
<!-- 浏览器阅读器开屏密码验证 -->
<div id="brStartupGate">
  <div class="br-startup-card">
    <div class="br-startup-icon">🔐</div>
    <div class="br-startup-title">浏览器阅读器已加密</div>
    <div class="br-startup-hint">请输入在设置中心设置的开屏密码，验证通过后才能进入并使用阅读器</div>
    <div class="br-pwd-row">
      <input type="password" class="br-startup-pwd" id="brStartupPwd" placeholder="请输入开屏密码" autocomplete="off" />
      <button type="button" class="br-startup-eye" id="brStartupEye" title="显示/隐藏密码" aria-label="显示或隐藏密码">
        <svg class="br-startup-eye-open" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></svg>
        <svg class="br-startup-eye-off" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
      </button>
    </div>
    <button class="br-startup-btn" id="brStartupBtn">进入阅读器</button>
    <div class="br-startup-msg" id="brStartupMsg"></div>
  </div>
</div>
"""

STARTUP_GATE_JS = r"""
/* === 浏览器阅读器开屏密码校验 === */
(function(){
  'use strict';
  if (window.__BR_STARTUP_PASSWORD_ENABLED__ !== true) return;

  var K = [
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
  ];
  var H0 = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];

  function brSha256Hex(str){
    var bytes;
    if (typeof TextEncoder !== 'undefined') { bytes = new TextEncoder().encode(str); }
    else {
      var bin = unescape(encodeURIComponent(str));
      bytes = [];
      for (var q=0;q<bin.length;q++) bytes.push(bin.charCodeAt(q));
    }
    var bitLen = bytes.length * 8;
    var total = ((bytes.length + 9 + 63) >> 6) << 6;
    var msg = new Uint8Array(total);
    msg.set(bytes);
    msg[bytes.length] = 0x80;
    var hi = Math.floor(bitLen / 4294967296), lo = bitLen >>> 0;
    msg[total-8]=(hi>>>24)&255; msg[total-7]=(hi>>>16)&255;
    msg[total-6]=(hi>>>8)&255;  msg[total-5]=hi&255;
    msg[total-4]=(lo>>>24)&255; msg[total-3]=(lo>>>16)&255;
    msg[total-2]=(lo>>>8)&255;  msg[total-1]=lo&255;
    var H = H0.slice(), w = new Int32Array(64);
    function rotr(x,n){ return (x>>>n)|(x<<(32-n)); }
    for (var off=0; off<total; off+=64){
      for (var t=0;t<16;t++){
        w[t]=(msg[off+t*4]<<24)|(msg[off+t*4+1]<<16)|(msg[off+t*4+2]<<8)|msg[off+t*4+3];
      }
      for (t=16;t<64;t++){
        var x=w[t-15], y=w[t-2];
        var s0=rotr(x,7)^rotr(x,18)^(x>>>3);
        var s1=rotr(y,17)^rotr(y,19)^(y>>>10);
        w[t]=(w[t-16]+s0+w[t-7]+s1)|0;
      }
      var a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
      for (t=0;t<64;t++){
        var S1=rotr(e,6)^rotr(e,11)^rotr(e,25);
        var ch=(e&f)^((~e)&g);
        var t1=(h+S1+ch+K[t]+w[t])|0;
        var S0=rotr(a,2)^rotr(a,13)^rotr(a,22);
        var maj=(a&b)^(a&c)^(b&c);
        var t2=(S0+maj)|0;
        h=g; g=f; f=e; e=(d+t1)|0; d=c; c=b; b=a; a=(t1+t2)|0;
      }
      H[0]=(H[0]+a)|0; H[1]=(H[1]+b)|0; H[2]=(H[2]+c)|0; H[3]=(H[3]+d)|0;
      H[4]=(H[4]+e)|0; H[5]=(H[5]+f)|0; H[6]=(H[6]+g)|0; H[7]=(H[7]+h)|0;
    }
    var hex='';
    for (var i=0;i<8;i++) hex += ('00000000'+(H[i]>>>0).toString(16)).slice(-8);
    return hex;
  }

  function brMsg(m){ var e=document.getElementById('brStartupMsg'); if(e) e.textContent=m||''; }
  function brToggleEye(){
    var btn=document.getElementById('brStartupEye'), inp=document.getElementById('brStartupPwd');
    if(!btn||!inp) return;
    var on=btn.classList.toggle('br-startup-eye-on');
    inp.type=on?'text':'password';
    if(on) inp.focus();
  }
  function brUnlock(){
    var inp=document.getElementById('brStartupPwd'), val=inp?inp.value:'';
    var expected=window.__BR_STARTUP_PASSWORD_HASH__||'';
    if(!val){ brMsg('请输入开屏密码'); return; }
    if(!expected){ brMsg('尚未在设置中心设置开屏密码，无法进入'); return; }
    if(brSha256Hex(val)!==expected){
      brMsg('开屏密码错误，请重试');
      if(inp){ inp.value=''; inp.focus(); }
      return;
    }
    brMsg('');
    /* file:// 页面里 document.cookie 不可用（或每个文件相互隔离），只写 cookie 会导致
       每打开一本书都要重新输密码。localStorage 在同一浏览器下跨 file:// 页面共享，
       作为主存储；摘要与当前密码哈希绑定，改密码后自动失效。 */
    try { localStorage.setItem('br_startup_unlocked_hash', expected); } catch(e){}
    try { document.cookie = 'br_startup_unlocked_hash=' + encodeURIComponent(expected) + '; Path=/; SameSite=Lax'; } catch(e){}
    try { sessionStorage.removeItem('br_startup_unlocked_hash'); } catch(e) {}
    document.documentElement.classList.remove('br-startup-locked');
    try { window.dispatchEvent(new Event('br-startup-unlocked')); } catch(e) {}
  }
  function brInit(){
    var btn=document.getElementById('brStartupBtn'); if(btn) btn.addEventListener('click', brUnlock);
    var inp=document.getElementById('brStartupPwd');
    if(inp){
      inp.addEventListener('keydown', function(e){ if(e.key==='Enter'){ e.preventDefault(); brUnlock(); } });
      inp.addEventListener('input', function(){ brMsg(''); });
      setTimeout(function(){ try{ inp.focus(); }catch(e){} }, 50);
    }
    var eye=document.getElementById('brStartupEye'); if(eye) eye.addEventListener('click', brToggleEye);
  }
  if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', brInit); }
  else { brInit(); }
})();
"""


# --------------------------------------------------------------------------- #
# 6. 局域网书库入口页（在线 / 离线共用同一页面）
# --------------------------------------------------------------------------- #
# 书库专属视觉层：只作用于入口页，不注入 file:// 阅读器页面。
# 放在 __RESPONSIVE_CSS__ 之后，可覆盖共享样式里的书库布局默认值。
PORTAL_CSS = r"""
:root{
  --br-accent:#4f7cff; --br-accent-soft:rgba(79,124,255,.10);
  --br-hero-a:#eef3ff; --br-hero-b:#f7f0ff;
  --br-chip-bg:#f1f4fa; --br-chip-fg:#5f6879; --br-tab-bg:#e9edf5;
  --br-nav-bg:rgba(255,255,255,.88);
}
html.br-dark{
  --br-page-bg:#0f1116; --br-page-fg:#e8ebf2; --br-card-bg:#191d26;
  --br-nav-border:#2a2f3a; --br-nav-fg:#dfe4ee;
  --br-accent:#7d9bff; --br-accent-soft:rgba(125,155,255,.13);
  --br-hero-a:#1a2440; --br-hero-b:#1b1a2c;
  --br-chip-bg:#222733; --br-chip-fg:#aab3c5; --br-tab-bg:#1d222c;
  --br-nav-bg:rgba(20,23,31,.88);
}

/* ---- 顶部 Hero ---- */
.br-portal-hero{
  position:relative; overflow:hidden; border-radius:22px; padding:22px 24px 18px;
  background:linear-gradient(120deg,var(--br-hero-a),var(--br-hero-b) 58%,var(--br-card-bg));
  border:1px solid var(--br-nav-border); box-shadow:0 10px 30px rgba(31,55,110,.06);
}
.br-portal-hero::before{
  content:''; position:absolute; right:-70px; top:-120px; width:260px; height:260px;
  border-radius:50%; background:radial-gradient(circle,rgba(84,124,255,.22),transparent 70%); pointer-events:none;
}
.br-portal-hero::after{
  content:''; position:absolute; left:36%; bottom:-150px; width:230px; height:230px;
  border-radius:50%; background:radial-gradient(circle,rgba(168,110,255,.14),transparent 70%); pointer-events:none;
}
.br-portal-hero > * { position:relative; z-index:1; }
.br-portal-hero-main{ display:flex; align-items:center; justify-content:space-between; gap:14px; flex-wrap:wrap; }
.br-portal-brand{ display:flex; align-items:center; gap:13px; min-width:0; }
.br-portal-logo{
  flex:0 0 46px; width:46px; height:46px; border-radius:14px; display:flex; align-items:center;
  justify-content:center; color:#fff; font-size:23px; font-weight:700; letter-spacing:-1px;
  background:linear-gradient(140deg,#4f7cff,#8b5cf6); box-shadow:0 6px 16px rgba(79,124,255,.32);
}
.br-portal-brand-text{ min-width:0; }
.br-portal-brand h1{ margin:0; font-size:23px; font-weight:700; letter-spacing:.5px; line-height:1.25; }
.br-portal-brand p{ margin:3px 0 0; font-size:12px; opacity:.58; }
.br-portal-hero-actions{ display:flex; align-items:center; gap:8px; margin-left:auto; }
.br-portal-hero .br-net-badge{
  display:inline-flex; align-items:center; gap:7px; font-size:12px; font-weight:600;
  padding:7px 11px; border-radius:999px; background:var(--br-card-bg);
  border:1px solid var(--br-nav-border); box-shadow:0 2px 8px rgba(31,55,110,.05);
}
.br-portal-hero .br-net-badge::before{ content:''; width:7px; height:7px; border-radius:50%; background:currentColor; }
.br-portal-hero .br-net-badge.online{ background:rgba(46,160,67,.12); color:#2ea043; }
.br-portal-hero .br-net-badge.offline{ background:rgba(220,80,60,.12); color:#d4503c; }
.br-portal-icon-btn{
  display:inline-flex; align-items:center; justify-content:center; gap:7px; height:38px; min-width:38px;
  padding:0 10px; border-radius:11px; border:1px solid var(--br-nav-border);
  background:var(--br-card-bg); color:inherit; cursor:pointer; font-size:13px;
  transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease;
}
.br-portal-icon-btn svg{ width:17px; height:17px; flex:0 0 17px; }
.br-portal-icon-btn span{ display:none; }
.br-portal-icon-btn:hover{ transform:translateY(-1px); border-color:var(--br-accent); box-shadow:0 5px 14px rgba(79,124,255,.16); }
.br-portal-icon-btn:active{ transform:scale(.96); }
.br-portal-hero-foot{ display:flex; align-items:center; gap:10px; margin-top:18px; font-size:12.5px; opacity:.8; flex-wrap:wrap; }
.br-portal-count{
  font-weight:650; font-size:12px; padding:5px 10px; border-radius:999px;
  background:var(--br-accent-soft); color:var(--br-accent); display:inline-flex; align-items:center;
}
.br-portal-divider{ width:1px; height:13px; background:var(--br-nav-border); opacity:.8; }

/* ---- 搜索 + 在线/离线分段控件 ---- */
.br-portal-controls{ display:flex; align-items:center; gap:12px; margin-top:18px; flex-wrap:wrap; }
.br-search-wrap{ position:relative; flex:1 1 260px; min-width:0; }
.br-search-icon{
  position:absolute; left:15px; top:50%; transform:translateY(-50%); width:17px; height:17px;
  color:var(--br-page-fg); opacity:.42; pointer-events:none;
}
.br-portal input[type=search]{
  height:46px; padding:0 14px 0 42px; border-radius:14px; font-size:14px;
  border:1px solid var(--br-nav-border); background:var(--br-card-bg); color:inherit;
  box-shadow:0 1px 2px rgba(16,24,40,.03); outline:none; transition:border-color .16s, box-shadow .16s;
}
.br-portal input[type=search]::placeholder{ opacity:.48; }
.br-portal input[type=search]:focus{ border-color:var(--br-accent); box-shadow:0 0 0 3px var(--br-accent-soft); }
.br-portal-tabs{
  display:inline-flex; align-items:center; gap:3px; padding:4px; border-radius:14px;
  background:var(--br-tab-bg); flex:0 0 auto;
}
.br-portal-tab{
  height:38px; padding:0 17px; border:0; border-radius:11px; background:transparent; color:inherit;
  font-size:13.5px; opacity:.62; cursor:pointer; white-space:nowrap; transition:all .16s ease;
}
.br-portal-tab:hover{ opacity:.9; }
.br-portal-tab.active{
  opacity:1; font-weight:650; color:var(--br-accent); background:var(--br-card-bg);
  box-shadow:0 2px 8px rgba(31,55,110,.10);
}
/* ---- 本地书籍管理（清理）---- */
.br-manage-local-btn{ display:none; }
.br-portal-tabs.manage-visible .br-manage-local-btn{ display:inline-flex; align-items:center; }
.br-local-manage-bar{
  display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-top:10px; padding:10px 12px;
  border-radius:12px; background:var(--br-card-bg); border:1px solid var(--br-nav-border);
}
.br-local-select-all{ display:inline-flex; align-items:center; gap:6px; font-size:13px; cursor:pointer; }
.br-local-manage-bar button{
  padding:6px 12px; border-radius:9px; border:1px solid var(--br-nav-border);
  background:transparent; color:inherit; cursor:pointer; font-size:13px;
}
.br-local-manage-bar button.br-local-danger{ color:#c0392b; border-color:#e6b0aa; }
html.br-dark .br-local-manage-bar button.br-local-danger{ color:#ff8a80; border-color:#7f3a33; }
.br-portal .book-card.select-mode{ cursor:default; }
.br-card-check{ display:none; align-items:center; justify-content:center; flex:0 0 auto; width:20px; height:20px; }
.br-portal.manage-mode .br-card-check{ display:flex; }
.br-portal.manage-mode .book-card{ cursor:pointer; }
.br-portal.manage-mode .book-card.selected{ outline:2px solid var(--br-accent); outline-offset:-2px; }
}

/* ---- 书籍卡片 ---- */
.br-portal .book-grid{ gap:14px; margin-top:18px; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); }
.br-portal .book-card{
  position:relative; display:flex; align-items:center; gap:14px; min-height:106px; padding:14px;
  border-radius:16px; background:var(--br-card-bg); border:1px solid var(--br-nav-border);
  box-shadow:0 1px 2px rgba(16,24,40,.03),0 8px 24px rgba(16,24,40,.045);
  overflow:hidden; transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
}
.br-portal .book-card::before{
  content:''; position:absolute; left:0; top:16px; bottom:16px; width:3px;
  border-radius:0 3px 3px 0; background:var(--br-accent); opacity:0; transition:opacity .18s ease;
}
@media (hover:hover){
  .br-portal .book-card:hover{ transform:translateY(-3px); border-color:rgba(79,124,255,.38); box-shadow:0 14px 30px rgba(31,55,110,.13); }
  .br-portal .book-card:hover::before{ opacity:1; }
  .br-portal .book-card:hover .book-arrow{ opacity:.9; transform:translateX(3px); }
}
.br-portal .book-card:active{ transform:scale(.992); }
.book-cover{
  flex:0 0 54px; width:54px; height:74px; border-radius:7px 10px 10px 7px;
  display:flex; align-items:center; justify-content:center; color:#fff; font-size:26px; font-weight:600;
  font-family:"Songti SC","STSong",Georgia,serif; text-shadow:0 1px 2px rgba(0,0,0,.18);
  background:linear-gradient(145deg,var(--cover-a),var(--cover-b));
  box-shadow:inset 4px 0 0 rgba(255,255,255,.18),inset -7px 0 12px rgba(0,0,0,.10),0 5px 12px rgba(20,30,60,.16);
  user-select:none;
}
.book-cover--0{--cover-a:#6a8dff;--cover-b:#8f6aff}
.book-cover--1{--cover-a:#ff9a76;--cover-b:#f2688f}
.book-cover--2{--cover-a:#37c2a6;--cover-b:#2e8fd6}
.book-cover--3{--cover-a:#f7b955;--cover-b:#ec7b4b}
.book-cover--4{--cover-a:#8e7bff;--cover-b:#5a6fe0}
.book-cover--5{--cover-a:#5bc0eb;--cover-b:#4b7ce8}
.book-meta{ flex:1 1 auto; min-width:0; }
.br-portal .book-card h3{
  margin:0 0 5px; font-size:15.5px; font-weight:650; line-height:1.4;
  display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:2;
  overflow:hidden; word-break:break-all;
}
.br-portal .book-card .book-author{
  margin:0; font-size:12.5px; opacity:.6; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.book-chips{ display:flex; flex-wrap:wrap; gap:6px; margin-top:9px; }
.book-chip{
  font-size:11px; line-height:1; padding:5px 8px; border-radius:6px; white-space:nowrap;
  background:var(--br-chip-bg); color:var(--br-chip-fg); border:1px solid var(--br-nav-border);
}
.book-chip--offline{ background:var(--br-accent-soft); color:var(--br-accent); border-color:transparent; }
.book-arrow{
  flex:0 0 auto; font-size:25px; line-height:1; color:var(--br-accent); opacity:.32;
  margin-left:2px; transition:transform .18s ease, opacity .18s ease; user-select:none;
}
.book-download{
  flex:0 0 auto; min-height:22px; padding:3px 8px; margin-left:0;
  border-radius:6px; border:1px solid var(--br-nav-border); background:var(--br-card-bg);
  color:var(--br-accent); font-size:11px; font-weight:650; white-space:nowrap; cursor:pointer;
}
.book-download:hover{ border-color:var(--br-accent); background:var(--br-accent-soft); }
.book-download:disabled{ opacity:.5; cursor:default; }

/* ---- 空状态 ---- */
.br-portal-empty{
  display:none; flex-direction:column; align-items:center; justify-content:center; gap:14px;
  padding:60px 16px; text-align:center; color:var(--br-page-fg); opacity:1;
}
.br-portal-empty-icon{
  width:54px; height:70px; border-radius:7px 11px 11px 7px; display:flex; align-items:center;
  justify-content:center; font-size:25px; color:#fff; font-family:"Songti SC","STSong",Georgia,serif;
  background:linear-gradient(145deg,#b9c8ee,#8fa4d6); box-shadow:0 10px 24px rgba(40,60,110,.18);
}
.br-portal-empty-text{ font-size:14px; opacity:.6; }

/* ---- 分页 ---- */
.br-portal-pager{ display:none; align-items:center; justify-content:center; flex-wrap:wrap; gap:6px; margin:22px 0 6px; }
.br-pager-numbers{ display:flex; align-items:center; gap:6px; }
.br-pager-btn,.br-pager-num{
  min-width:36px; height:36px; padding:0 10px; border-radius:10px; border:1px solid var(--br-nav-border);
  background:var(--br-card-bg); color:inherit; font-size:14px; cursor:pointer;
  display:inline-flex; align-items:center; justify-content:center; transition:all .16s ease;
}
.br-pager-btn{ font-size:19px; line-height:1; }
.br-pager-btn:hover:not(:disabled),.br-pager-num:hover:not(.active){
  border-color:var(--br-accent); color:var(--br-accent); transform:translateY(-1px);
}
.br-pager-btn:disabled{ opacity:.35; cursor:default; }
.br-pager-num.active{
  background:var(--br-accent); border-color:var(--br-accent); color:#fff; font-weight:650;
  box-shadow:0 4px 12px rgba(79,124,255,.24);
}
.br-pager-ellipsis{ padding:0 4px; opacity:.5; font-size:13px; }
.br-pager-info{ font-size:12.5px; opacity:.6; margin-left:8px; white-space:nowrap; }

/* ---- 底部导航（仅书库页） ---- */
.br-portal-nav{
  background:var(--br-nav-bg); backdrop-filter:saturate(180%) blur(16px);
  -webkit-backdrop-filter:saturate(180%) blur(16px);
  border-top:1px solid var(--br-nav-border); box-shadow:0 -6px 24px rgba(16,24,40,.06);
}
.br-portal-nav button.active::before{
  content:''; position:absolute; top:0; left:50%; transform:translateX(-50%);
  width:26px; height:3px; border-radius:0 0 3px 3px; background:var(--br-accent);
}
.br-portal-nav button.active{ position:relative; }
html.br-dark .br-portal-nav{ --br-nav-bg:rgba(20,23,31,.88); --br-nav-fg:#dfe4ee; }
html.br-dark .br-portal-icon-btn{ background:rgba(255,255,255,.06); }
html.br-dark .br-portal .book-card{ box-shadow:0 8px 24px rgba(0,0,0,.22); }

/* ---- 全屏设置页 / 离线阅读页与书库同一套配色 ---- */
.br-settings-view.open{ background:var(--br-page-bg); color:var(--br-page-fg); }
.br-portal-offline-reader.open{ background:var(--br-page-bg); color:var(--br-page-fg); }

@media (min-width:769px){
  .br-portal-icon-btn span{ display:inline; }
  .br-portal-hero{ padding:26px 28px 20px; }
  .br-portal-brand h1{ font-size:26px; }
  /* 宽屏独立设置页沿用书库的圆角卡片与按钮语言 */
  .br-settings-view.open .br-setting-row input[type=range]{ flex:1 1 220px; }
  .br-settings-view.open .br-setting-row .br-value{ min-width:44px; text-align:right; font-size:13px; opacity:.65; }
  .br-settings-view.open .br-setting-actions button{
    min-height:42px; padding:0 18px; font-size:14px; cursor:pointer;
    transition:transform .16s ease, box-shadow .16s ease;
  }
  .br-settings-view.open .br-setting-actions button:hover{ transform:translateY(-1px); box-shadow:0 6px 16px rgba(31,55,110,.12); }
  .br-settings-view.open .br-setting-actions button.primary{
    background:var(--br-accent); border-color:var(--br-accent); color:#fff; font-weight:650;
  }
}
@media (max-width:768px){
  .br-portal .book-grid{ grid-template-columns:1fr; gap:10px; margin-top:14px; }
  .br-portal-hero{ border-radius:18px; padding:18px 16px 15px; }
  .br-portal-hero-main{ flex-wrap:nowrap; gap:8px; }
  .br-portal-brand{ flex:1 1 auto; }
  .br-portal-brand-text{ overflow:hidden; }
  .br-portal-logo{ flex-basis:42px; width:42px; height:42px; font-size:21px; border-radius:12px; }
  .br-portal-brand h1{ font-size:20px; }
  .br-portal-brand p{ font-size:11.5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .br-portal-hero-actions{ flex:0 0 auto; gap:6px; }
  .br-portal-hero .br-net-badge{ padding:6px 9px; font-size:11px; }
  .br-portal-icon-btn{ height:34px; min-width:34px; padding:0 7px; }
  /* 手机端设置走底部导航的独立页面，Hero 里只保留刷新，避免按钮过挤 */
  .br-portal-hero .br-portal-settings-btn{ display:none; }
  .br-portal-hero-foot{ margin-top:14px; }
  .br-portal-controls{ margin-top:14px; gap:10px; }
  .br-search-wrap{ flex-basis:100%; }
  .br-portal-tabs{ width:100%; }
  .br-portal-tab{ flex:1; padding:0 8px; }
  .br-portal .book-card{ min-height:96px; padding:12px; gap:12px; border-radius:14px; }
  .book-cover{ flex-basis:48px; width:48px; height:66px; font-size:23px; }
  .br-portal .book-card h3{ font-size:15px; }
  .br-portal-pager{ gap:5px; margin:18px 0 4px; }
  .br-pager-btn,.br-pager-num{ min-width:34px; height:34px; border-radius:9px; padding:0 8px; }
  .br-pager-info{ width:100%; text-align:center; margin:8px 0 0; }
}
@media (prefers-reduced-motion:reduce){
  .br-portal .book-card,.br-portal-icon-btn,.br-portal-tab,.book-arrow,
  .br-pager-btn,.br-pager-num{ transition:none !important; }
}
"""

# 网络版书库页 + 离线/网络阅读页共用的右侧固定滚动按钮。
# position:fixed 让按钮相对视口定位，页面上下滚动时不会跟着移动。
SCROLL_NAV_CSS = r"""
.br-scroll-nav {
  position: fixed; right: 16px; top: 50%; transform: translateY(-50%);
  display: flex; flex-direction: column; gap: 8px; z-index: 8000;
}
.br-scroll-btn {
  width: 38px; height: 38px; border-radius: 50%; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; line-height: 1; font-weight: 600;
  color: var(--reader-text, var(--br-page-fg, #222));
  background: var(--reader-bg, var(--br-page-bg, #fff));
  border: 1px solid rgba(128,128,128,.38);
  box-shadow: 0 2px 10px rgba(0,0,0,.16);
  opacity: .88; transition: opacity .15s, transform .15s, background .15s;
  padding: 0; -webkit-appearance: none; appearance: none;
}
.br-scroll-btn:hover { opacity: 1; transform: scale(1.06); }
.br-scroll-btn:active { transform: scale(.96); }
.br-scroll-btn:focus-visible { outline: 2px solid var(--br-accent, #4f7cff); outline-offset: 2px; }
@media (max-width: 640px) {
  .br-scroll-nav { right: 8px; gap: 6px; }
  .br-scroll-btn { width: 34px; height: 34px; font-size: 16px; }
}
"""

SCROLL_NAV_HTML = r"""
<div class="br-scroll-nav" aria-label="页面滚动 / Page scroll">
  <button type="button" class="br-scroll-btn" id="brScrollTopBtn" title="回到顶部 / Top" aria-label="回到顶部">↑</button>
  <button type="button" class="br-scroll-btn" id="brScrollBottomBtn" title="去底部 / Bottom" aria-label="去底部">↓</button>
</div>
"""

SCROLL_NAV_JS = r"""
(function(){
  function scrollHost(){
    var candidates = [];
    var offline = document.getElementById('offlineReader');
    if (offline && offline.classList && offline.classList.contains('open')) candidates.push(offline);
    var sync = document.querySelector('.br-sync-list');
    if (sync && sync.offsetParent !== null) candidates.push(sync);
    var page = document.querySelector('.page.active .page-content') || document.querySelector('.page-content');
    if (page) candidates.push(page);
    var content = document.getElementById('content');
    if (content) candidates.push(content);
    for (var i = 0; i < candidates.length; i++) {
      var el = candidates[i];
      var st = window.getComputedStyle(el);
      if ((st.overflowY === 'auto' || st.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 2) return el;
    }
    return null;
  }
  function go(to){
    /* 书库页的离线阅读器可能是 iframe，优先滚动 iframe 内部文档 */
    var iframe = document.querySelector('.br-portal-offline-reader iframe, #offlineReader iframe');
    if (iframe) {
      try {
        var iw = iframe.contentWindow;
        var idoc = iframe.contentDocument;
        var iel = idoc && (idoc.scrollingElement || idoc.body);
        if (iw) {
          iw.scrollTo({ top: to === 'top' ? 0 : (iel ? iel.scrollHeight : 1e9), behavior: 'smooth' });
          return;
        }
      } catch(e) {}
    }
    var el = scrollHost();
    if (el) {
      el.scrollTo({ top: to === 'top' ? 0 : el.scrollHeight, behavior: 'smooth' });
    } else {
      var doc = document.documentElement || document.body;
      window.scrollTo({ top: to === 'top' ? 0 : doc.scrollHeight, behavior: 'smooth' });
    }
  }
  function bind(){
    var top = document.getElementById('brScrollTopBtn');
    var bottom = document.getElementById('brScrollBottomBtn');
    if (top) top.addEventListener('click', function(){ go('top'); });
    if (bottom) bottom.addEventListener('click', function(){ go('bottom'); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();
"""

# 统一运行时：网络版 / 离线版共用同一份 URL、密钥与 API 地址逻辑。
# 上层组件只调用 window.BRAppRuntime，不再散落判断 location.protocol / OFFLINE。
APP_RUNTIME_JS = r"""
(function () {
  'use strict';
  var KEY_STORE = 'br_api_secret', BACK_STORE = 'br_backend_override';
  function safe(fn) { try { return fn(); } catch (e) { return null; } }
  function isFile() { return location.protocol === 'file:'; }
  function key() {
    return safe(function () { return localStorage.getItem(KEY_STORE); }) ||
      window.__BR_BOOT_SECRET__ || '';
  }
  function defaultBackend() {
    return window.__BR_DEFAULT_BACKEND__ || 'http://127.0.0.1:54321';
  }
  function backend() {
    var override = safe(function () { return localStorage.getItem(BACK_STORE); });
    var base = override || (isFile() ? defaultBackend() : location.origin);
    return String(base || '').replace(/\/+$/, '');
  }
  function withKey(url) {
    var k = key();
    return k ? url + (url.indexOf('?') >= 0 ? '&' : '?') + 'key=' + encodeURIComponent(k) : url;
  }
  function apiHeaders() {
    var h = { 'Content-Type': 'application/json' };
    var k = key();
    if (k) { h['X-API-Key'] = k; }
    return h;
  }
  function apiUrl(path) { return backend() + (path.charAt(0) === '/' ? path : '/' + path); }
  function readerUrl(bookKey) {
    if (!bookKey) { return ''; }
    if (isFile()) {
      var suffix = key() ? '&key=' + encodeURIComponent(key()) : '';
      return backend() + '/reader?book=' + encodeURIComponent(bookKey) + suffix;
    }
    return withKey('/reader?book=' + encodeURIComponent(bookKey));
  }
  function libraryUrl() {
    if (isFile()) { return location.href.split('?')[0].split('#')[0]; }
    return withKey('/');
  }
  window.BRAppRuntime = {
    isFile: isFile,
    key: key,
    backend: backend,
    withKey: withKey,
    apiHeaders: apiHeaders,
    apiUrl: apiUrl,
    readerUrl: readerUrl,
    libraryUrl: libraryUrl
  };
})();
"""

# 数据适配层：上层 UI 只调用 BRDataSource，不再直接使用 fetch / IndexedDB 细节。
DATA_SOURCE_JS = r"""
(function () {
  'use strict';
  var rt = window.BRAppRuntime;
  var DB_NAME = 'br_offline_books', STORE = 'books', HISTORY_KEY = 'readingHistory';

  function jsonFetch(url, options) {
    return fetch(url, options).then(function (r) {
      if (!r.ok) { throw new Error('HTTP ' + r.status); }
      return r.json();
    });
  }
  function openDB() {
    return new Promise(function (resolve, reject) {
      if (!window.indexedDB) { reject(new Error('no-idb')); return; }
      var req = indexedDB.open(DB_NAME, 3);
      req.onupgradeneeded = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains(STORE)) { db.createObjectStore(STORE, { keyPath: 'id' }); }
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }
  function txDone(tx) {
    return new Promise(function (resolve) {
      tx.oncomplete = function () { resolve(true); };
      tx.onerror = function () { resolve(false); };
    });
  }

  var HttpDataSource = {
    health: function () {
      return jsonFetch(rt.apiUrl('/health_check'), { cache: 'no-store' })
        .then(function (d) { return !!(d && d.status === 'ok'); })
        .catch(function () { return false; });
    },
    listBooks: function (page, pageSize, keyword) {
      var url = rt.apiUrl('/api/portal/books') + '?page=' + encodeURIComponent(page) +
        '&page_size=' + encodeURIComponent(pageSize) +
        (keyword ? '&q=' + encodeURIComponent(keyword) : '');
      return jsonFetch(rt.withKey(url), { headers: rt.apiHeaders(), cache: 'no-store' });
    },
    bookIndex: function () {
      return jsonFetch(rt.withKey(rt.apiUrl('/api/portal/books/index')), {
        headers: rt.apiHeaders(), cache: 'no-store'
      });
    },
    downloadBook: function (bookKey) {
      var url = rt.withKey(rt.apiUrl('/download_book') + '?book=' + encodeURIComponent(bookKey));
      return fetch(url, { headers: rt.apiHeaders(), cache: 'no-store' }).then(function (r) {
        if (!r.ok) { throw new Error('HTTP ' + r.status); }
        return r.blob().then(function (blob) {
          return { blob: blob, cd: r.headers.get('Content-Disposition') || '' };
        });
      });
    },
    uploadBook: function (blob, fileName, title) {
      var h = {
        'Content-Type': 'application/octet-stream',
        'X-File-Name': encodeURIComponent(fileName),
        'X-File-Title': encodeURIComponent(title || fileName.replace(/\.[^.]+$/, ''))
      };
      var k = rt.key();
      if (k) { h['X-API-Key'] = k; }
      var url = rt.withKey(rt.apiUrl('/api/upload_book'));
      return jsonFetch(url, { method: 'POST', headers: h, body: blob, cache: 'no-store' });
    }
  };

  var LocalDataSource = {
    openDB: openDB,
    listBooks: function () {
      return openDB().then(function (db) {
        return new Promise(function (resolve) {
          var tx = db.transaction(STORE, 'readonly');
          var req = tx.objectStore(STORE).getAll();
          req.onsuccess = function () { db.close(); resolve(req.result || []); };
          req.onerror = function () { db.close(); resolve([]); };
        });
      }).catch(function () { return []; });
    },
    getBook: function (key) {
      return openDB().then(function (db) {
        return new Promise(function (resolve) {
          var req = db.transaction(STORE, 'readonly').objectStore(STORE).get(key);
          req.onsuccess = function () { db.close(); resolve(req.result || null); };
          req.onerror = function () { db.close(); resolve(null); };
        });
      }).catch(function () { return null; });
    },
    saveBook: function (record) {
      return openDB().then(function (db) {
        var tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).put(record);
        return txDone(tx).then(function (ok) { db.close(); return ok; });
      }).catch(function () { return false; });
    },
    history: function () {
      try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch (e) { return []; }
    },
    saveHistory: function (items) {
      try { localStorage.setItem(HISTORY_KEY, JSON.stringify(items || [])); return true; }
      catch (e) { return false; }
    },
    deleteHistory: function (keys) {
      var list = Object.keys(keys || {}).filter(function (k) { return !!k; });
      if (!list.length) { return false; }
      var remain = this.history().filter(function (h) {
        var k = String(h.bookId || h.id || '');
        return list.indexOf(k) < 0;
      });
      return this.saveHistory(remain);
    },
    clearHistory: function () {
      return this.saveHistory([]);
    }
  };

  window.BRDataSource = { http: HttpDataSource, local: LocalDataSource };
})();
"""

# 统一 App Shell：书库视图与阅读视图容器。阅读器旧页面暂时用 iframe 承载，
# 后续 Phase 3 再把阅读功能逐个搬进统一壳，保证功能不丢失。
APP_SHELL_CSS = r"""
.app-view { display: none; }
.app-view.active { display: block; }
#appReaderView {
  position: fixed; inset: 0; z-index: 5000;
  background: var(--br-page-bg, #fff);
}
#appReaderFrame { width: 100%; height: 100%; border: 0; display: block; }
#appReaderBackBtn {
  position: fixed; left: 14px; top: 50%; transform: translateY(-50%);
  z-index: 5200; padding: 9px 12px; border-radius: 20px; cursor: pointer;
  color: var(--br-page-fg, #222); background: var(--br-card-bg, #fff);
  border: 1px solid rgba(128,128,128,.35); box-shadow: 0 2px 10px rgba(0,0,0,.18);
}
#appPanelBackdrop { position: absolute; inset: 0; z-index: 5203; background: rgba(0,0,0,.28); }
#appPanelBackdrop[hidden] { display: none; }
.br-app-toolbar {
  position: absolute; left: 50%; top: 12px; transform: translateX(-50%);
  z-index: 5204; display: flex; gap: 6px; padding: 6px 8px; border-radius: 24px;
  background: var(--br-card-bg, #fff); border: 1px solid rgba(128,128,128,.35);
  box-shadow: 0 3px 14px rgba(0,0,0,.2); max-width: calc(100vw - 90px); overflow-x: auto;
}
.br-app-toolbar button {
  cursor: pointer; white-space: nowrap; padding: 5px 10px; border-radius: 16px;
  border: 1px solid rgba(128,128,128,.25); background: transparent;
  color: var(--br-page-fg, #222); font-size: 13px;
}
.br-app-toolbar button:hover { background: rgba(128,128,128,.12); }
.br-app-settings {
  position: absolute; right: 16px; top: 58px; z-index: 5205;
  width: 260px; padding: 14px; border-radius: 12px;
  background: var(--br-card-bg, #fff); color: var(--br-page-fg, #222);
  border: 1px solid rgba(128,128,128,.35); box-shadow: 0 6px 24px rgba(0,0,0,.24);
}
.br-app-settings[hidden] { display: none; }
.br-app-settings h3 { margin: 0 0 10px; font-size: 15px; }
.br-app-settings .br-app-setting-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.br-app-settings button { cursor: pointer; padding: 5px 9px; border-radius: 8px; border: 1px solid rgba(128,128,128,.3); background: transparent; color: inherit; }
.br-app-settings button.active { background: rgba(79,172,254,.22); border-color: rgba(79,172,254,.65); }
.br-app-progress-sync-settings { margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(128,128,128,.25); }
.br-app-progress-sync-settings[hidden] { display: none; }
.br-app-setting-line { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-height: 30px; font-size: 13px; }
.br-app-setting-line > span:last-child { color: var(--br-accent, #4f7cff); text-align: right; word-break: break-all; }
.br-app-setting-line select { max-width: 120px; padding: 4px 6px; border-radius: 8px; border: 1px solid rgba(128,128,128,.3); background: transparent; color: inherit; }
#appTocPanel { left: 16px; right: auto; width: 300px; max-height: calc(100vh - 90px); overflow-y: auto; }
#appTocPanel input { width: 100%; padding: 6px 8px; margin-bottom: 8px; border-radius: 8px; border: 1px solid rgba(128,128,128,.3); background: transparent; color: inherit; }
#appTocList { list-style: none; padding: 0; margin: 0; }
#appTocList li { padding: 6px 8px; cursor: pointer; border-radius: 6px; font-size: 13px; }
#appTocList li:hover { background: rgba(128,128,128,.12); }
#appTocList li.h2 { padding-left: 18px; }
#appTocList li.h3 { padding-left: 30px; }
#appSearchPanel { right: 16px; left: auto; width: 360px; max-height: calc(100vh - 90px); overflow-y: auto; }
#appSearchPanel input { width: 100%; padding: 6px 8px; margin-bottom: 8px; border-radius: 8px; border: 1px solid rgba(128,128,128,.3); background: transparent; color: inherit; }
#appSearchList { list-style: none; padding: 0; margin: 0; }
#appSearchList li { padding: 6px 8px; cursor: pointer; border-radius: 6px; font-size: 13px; line-height: 1.5; }
#appSearchList li:hover { background: rgba(128,128,128,.12); }
#appBookmarkPanel, #appNotePanel, #appHighlightPanel, #appVocabPanel, #appSpeechPanel, #appProgressPanel, #appViewModePanel, #appJumpPanel, #appUnlockPanel { right: 16px; left: auto; width: 360px; max-height: calc(100vh - 90px); overflow-y: auto; }
#appNotePanel textarea, #appVocabPanel input, #appSpeechPanel select, #appProgressPanel input, #appJumpPanel input, #appUnlockPanel input, #appThemeSelect { width: 100%; box-sizing: border-box; padding: 6px 8px; margin-bottom: 8px; border-radius: 8px; border: 1px solid rgba(128,128,128,.3); background: transparent; color: inherit; resize: vertical; }
#appSpeechPanel input[type="range"] { width: 100%; }
#appSpeechStatus { min-height: 18px; margin-bottom: 8px; font-size: 12px; opacity: .75; }
#appProgressTrack { height: 8px; border-radius: 6px; background: rgba(128,128,128,.2); overflow: hidden; margin-bottom: 6px; }
#appProgressFill { height: 100%; width: 0; background: #4facfe; transition: width .2s ease; }
#appProgressMeta { margin-bottom: 8px; font-size: 12px; opacity: .75; }
#appToast { position: absolute; left: 50%; bottom: 24px; transform: translateX(-50%); z-index: 5300; padding: 8px 14px; border-radius: 10px; background: rgba(20,20,20,.88); color: #fff; font-size: 13px; pointer-events: none; }
#appToast[hidden] { display: none; }
.app-annotation-list { list-style: none; padding: 0; margin: 0 0 8px; }
.app-annotation-list li { position: relative; padding: 7px 28px 7px 8px; cursor: pointer; border-radius: 6px; font-size: 13px; line-height: 1.5; border-bottom: 1px solid rgba(128,128,128,.12); }
.app-annotation-list li:hover { background: rgba(128,128,128,.12); }
.app-annotation-list .app-annotation-title { font-weight: 600; }
.app-annotation-list .app-annotation-quote { margin-top: 3px; opacity: .75; font-size: 12px; }
.app-annotation-list .app-annotation-meta { margin-top: 3px; opacity: .6; font-size: 11px; }
.app-annotation-list .app-annotation-delete { position: absolute; right: 6px; top: 6px; border: 0; padding: 1px 6px; font-size: 16px; line-height: 1.2; }
#appReaderFrame { padding-top: 52px; }
body.app-reader-active .br-scroll-nav { display: none; }
.br-app-settings { animation: brPanelIn .14s ease-out; }
@keyframes brPanelIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 720px) {
  .br-app-toolbar { left: 8px; right: 8px; transform: none; max-width: none; justify-content: flex-start; }
  .br-app-toolbar button { padding: 5px 8px; font-size: 12px; }
  #appReaderBackBtn { top: auto; bottom: 12px; left: 8px; transform: none; padding: 7px 10px; }
  .br-app-settings, #appTocPanel, #appSearchPanel,
  #appBookmarkPanel, #appNotePanel, #appHighlightPanel, #appVocabPanel,
  #appSpeechPanel, #appProgressPanel, #appViewModePanel, #appJumpPanel,
  #appUnlockPanel { left: 8px !important; right: 8px !important; width: auto !important; top: 58px; max-height: calc(100vh - 120px); }
}

/* 打开书籍前的全屏遮罩：后端动态 reader 首次生成可能要数秒，先给出明确反馈。 */
#brLoadingMask { position: fixed; inset: 0; z-index: 99999; display: none; align-items: center; justify-content: center; background: rgba(16,20,34,.55); backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); color: #fff; }
.br-loading-card { display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 28px 34px; max-width: 84vw; border-radius: 16px; background: rgba(26,30,46,.94); box-shadow: 0 18px 48px rgba(0,0,0,.38); }
.br-loading-spinner { width: 40px; height: 40px; border-radius: 50%; border: 3px solid rgba(255,255,255,.22); border-top-color: #4f7cff; animation: brLoadingSpin .8s linear infinite; }
.br-loading-text { font-size: 14px; line-height: 1.5; text-align: center; }
@keyframes brLoadingSpin { to { transform: rotate(360deg); } }
"""

APP_ROUTER_JS = r"""
(function () {
  'use strict';
  var current = 'library', currentSrc = '';
  function params() {
    var out = {};
    new URLSearchParams(location.search).forEach(function (v, k) { out[k] = v; });
    var hash = String(location.hash || '').replace(/^#\/?/, '');
    if (hash) { new URLSearchParams(hash).forEach(function (v, k) { out[k] = v; }); }
    return out;
  }
  function updateUrl(view, book, src, push) {
    if (location.protocol === 'file:') {
      var h = '#view=' + encodeURIComponent(view);
      if (book) { h += '&book=' + encodeURIComponent(book); }
      if (src) { h += '&src=' + encodeURIComponent(src); }
      if (push) { location.hash = h; }
      else {
        try { history.replaceState(null, '', location.pathname + h); }
        catch (e) { location.hash = h; }
      }
      return;
    }
    var p = new URLSearchParams(location.search);
    p.set('view', view);
    if (book) { p.set('book', book); } else { p.delete('book'); }
    if (src) { p.set('src', src); } else { p.delete('src'); }
    var url = location.pathname + '?' + p.toString();
    if (push) { history.pushState(null, '', url); }
    else { history.replaceState(null, '', url); }
  }
  /* 显式同步阅读视图的界面状态，不单纯依赖 body class：
     工具栏(.br-app-toolbar)在阅读视图必须可见，右下角滚动导航(.br-scroll-nav)
     在阅读视图必须隐藏。个别浏览器在 iframe 加载/整页刷新后 body class 与
     视图状态可能短暂不同步，表现为“进入阅读后顶部菜单消失、只剩返回按钮和
     右侧滚动按钮”，这里用 inline style 兜底，确保状态一致。 */
  function syncReaderChrome(inReader) {
    var toolbar = document.getElementById('appReaderToolbar');
    var back = document.getElementById('appReaderBackBtn');
    var scrollNav = document.querySelector('.br-scroll-nav');
    var lib = document.getElementById('appLibraryView');
    var reader = document.getElementById('appReaderView');
    /* 视图容器也用 inline style 同步：截图里出现“URL 已是 #view=library 但
       阅读 iframe 仍可见、工具栏却消失”的矛盾态，即 .active class 与
       app-reader-active 脱节。直接控制 display 保证二者严格一致。 */
    if (reader) { reader.style.display = inReader ? 'block' : 'none'; }
    if (lib) { lib.style.display = inReader ? 'none' : 'block'; }
    if (toolbar) { toolbar.style.display = inReader ? 'flex' : 'none'; }
    if (back) { back.style.display = inReader ? 'block' : 'none'; }
    if (scrollNav) { scrollNav.style.display = inReader ? 'none' : 'flex'; }
    if (inReader) { if (reader) { reader.classList.add('active'); } if (lib) { lib.classList.remove('active'); } }
    else { if (reader) { reader.classList.remove('active'); } if (lib) { lib.classList.add('active'); } }
    document.body.classList.toggle('app-reader-active', !!inReader);
  }
  function showLibrary(push) {
    current = 'library';
    currentSrc = '';
    syncReaderChrome(false);
    hideAllAppPanels();
    updateUrl('library', '', '', push !== false);
  }
  function showReader(bookKey, src, push) {
    if (!bookKey && !src) { return; }
    current = 'reader';
    currentSrc = src || currentSrc;
    var frame = document.getElementById('appReaderFrame');
    syncReaderChrome(true);
    if (frame) {
      frame.src = currentSrc || window.BRAppRuntime.readerUrl(bookKey);
    }
    updateUrl('reader', bookKey, currentSrc, push !== false);
    /* iframe 加载 / hashchange 可能在下一帧回退状态，延迟再确认一次 */
    setTimeout(function () {
      if (current === 'reader') { syncReaderChrome(true); }
    }, 0);
    setTimeout(function () {
      if (current === 'reader') { syncReaderChrome(true); }
    }, 300);
  }
  /* 设置页用 #settings 作为 hash；它不是阅读路由，APP_ROUTER 必须忽略，
     否则 hashchange → start() 会把它当成「非阅读」而调用 showLibrary()，
     把刚打开的设置面板立刻关掉（表现为点设置按钮页面一闪）。 */
  function isSettingsHash() {
    var h = String(location.hash || '');
    return h === '#settings' || h === '#/settings' || h.indexOf('#settings&') === 0;
  }
  function start() {
    if (isSettingsHash()) { return current === 'reader'; }
    var p = params();
    if (p.view === 'reader' || p.book) {
      /* 旧缓存曾把书名写进 book 参数；这类 key 后端无法识别，
         刷新到错误 URL 时直接回书库，避免再次落到 404 页面。 */
      if (p.book && !/^[0-9a-f]{20}$/i.test(String(p.book).trim()) &&
          !(p.src || currentSrc)) {
        showLibrary(false);
        return false;
      }
      showReader(p.book || '', p.src || currentSrc, false);
      return true;
    }
    showLibrary(false);
    return false;
  }
  window.addEventListener('popstate', function () { if (!isSettingsHash()) { start(); } });
  window.addEventListener('hashchange', function () { if (!isSettingsHash()) { start(); } });
  /* 兜底：以顶层 URL hash 为唯一真相校正视图状态。
     file:// 下 iframe 是独立 origin，父页面读 contentWindow.location.href 会抛
     SecurityError（实测），无法探测 iframe 内部导航；postMessage 超时也不能作为
     “已离开阅读页”的依据（旧版阅读页不会应答，会误伤）。因此这里只根据顶层
     hash 判断：URL 已是 library 视图时，确保书库可见、阅读视图与工具栏隐藏，
     消除“URL=#view=library 但正文仍显示”的脱节态。 */
  function reconcileViewFromHash() {
    if (isSettingsHash()) { return; } /* 设置页不是阅读路由，勿按其 hash 校正视图 */
    var p = params();
    var wantReader = (p.view === 'reader' || !!p.book);
    if (wantReader && current !== 'reader') { showReader(p.book || '', p.src || currentSrc, false); }
    else if (!wantReader && current !== 'library') { showLibrary(false); }
    else { syncReaderChrome(wantReader); }
  }
  window.addEventListener('DOMContentLoaded', function () {
    setTimeout(reconcileViewFromHash, 50);
    setTimeout(reconcileViewFromHash, 400);
    /* 低频兜底轮询：仅当 hash 与视图状态不一致才动作，正常时不改 DOM。
       覆盖 replaceState 改 hash 不触发 hashchange、或 iframe 导航导致状态脱节。 */
    setInterval(function () {
      var p = params();
      var wantReader = (p.view === 'reader' || !!p.book);
      var readerView = document.getElementById('appReaderView');
      var actuallyReader = !!(readerView && readerView.classList.contains('active') &&
        getComputedStyle(readerView).display !== 'none');
      if (wantReader !== actuallyReader) { reconcileViewFromHash(); }
    }, 700);
  });
  var tocItems = [];
  function requestToc() {
    var frame = document.getElementById('appReaderFrame');
    if (frame && frame.contentWindow) {
      frame.contentWindow.postMessage({ source: 'br-app-shell', action: 'toc-request' }, '*');
    }
  }
  function renderToc(items) {
    tocItems = items || [];
    var list = document.getElementById('appTocList');
    if (!list) { return; }
    list.innerHTML = '';
    tocItems.forEach(function (item, index) {
      var li = document.createElement('li');
      li.className = item.tag || '';
      li.textContent = item.title || ('章节 ' + (index + 1));
      li.setAttribute('data-index', String(index));
      li.addEventListener('click', function () {
        sendReaderAction('toc-jump', String(index));
      });
      list.appendChild(li);
    });
  }
  function renderSearchResults(items) {
    var list = document.getElementById('appSearchList');
    if (!list) { return; }
    list.innerHTML = '';
    (items || []).forEach(function (item) {
      var li = document.createElement('li');
      li.textContent = item.text || '';
      li.addEventListener('click', function () {
        sendReaderAction('search-goto', String(item.index || 0));
      });
      list.appendChild(li);
    });
    if (!(items || []).length) {
      var li = document.createElement('li');
      li.textContent = '未找到匹配内容';
      list.appendChild(li);
    }
  }
  function requestBookmarks() { sendReaderAction('bookmarks-request'); }
  function requestNotes() { sendReaderAction('notes-request'); }
  function formatAnnotationTime(value) {
    if (!value) { return ''; }
    var n = Number(value);
    return isFinite(n) && n > 0 ? new Date(n).toLocaleString() : String(value);
  }
  function renderAnnotationList(list, items, type) {
    if (!list) { return; }
    list.innerHTML = '';
    (items || []).forEach(function (item, index) {
      var li = document.createElement('li');
      var title = document.createElement('div');
      title.className = 'app-annotation-title';
      title.textContent = type === 'bookmark'
        ? (item.name || ('书签 ' + (index + 1)))
        : (item.text || ('笔记 ' + (index + 1)));
      li.appendChild(title);
      if (type === 'note' && item.quote) {
        var quote = document.createElement('div');
        quote.className = 'app-annotation-quote';
        quote.textContent = '“' + item.quote + '”';
        li.appendChild(quote);
      }
      var meta = document.createElement('div');
      meta.className = 'app-annotation-meta';
      meta.textContent = formatAnnotationTime(item.time) + (item.position != null ? ' · 位置 ' + item.position : '');
      li.appendChild(meta);
      var del = document.createElement('button');
      del.type = 'button';
      del.className = 'app-annotation-delete';
      del.textContent = '×';
      del.title = '删除';
      del.addEventListener('click', function (e) {
        e.stopPropagation();
        sendReaderAction(type + '-delete', String(item.id != null ? item.id : index));
      });
      li.appendChild(del);
      li.addEventListener('click', function () {
        sendReaderAction(type + '-jump', String(item.position || 0));
      });
      list.appendChild(li);
    });
    if (!(items || []).length) {
      var empty = document.createElement('li');
      empty.textContent = type === 'bookmark' ? '暂无书签' : '暂无笔记';
      list.appendChild(empty);
    }
  }
  function renderBookmarks(items) { renderAnnotationList(document.getElementById('appBookmarkList'), items, 'bookmark'); }
  function renderNotes(items) { renderAnnotationList(document.getElementById('appNoteList'), items, 'note'); }
  function requestHighlights() { sendReaderAction('highlights-request'); }
  function renderHighlights(items) {
    var list = document.getElementById('appHighlightList');
    if (!list) { return; }
    list.innerHTML = '';
    (items || []).forEach(function (item, index) {
      var li = document.createElement('li');
      var text = document.createElement('div');
      text.className = 'app-annotation-title';
      text.textContent = item.text || ('高亮 ' + (index + 1));
      li.appendChild(text);
      var meta = document.createElement('div');
      meta.className = 'app-annotation-meta';
      meta.textContent = formatAnnotationTime(item.time) + (item.position != null ? ' · 位置 ' + item.position : '');
      li.appendChild(meta);
      var del = document.createElement('button');
      del.type = 'button';
      del.className = 'app-annotation-delete';
      del.textContent = '×';
      del.title = '删除';
      del.addEventListener('click', function (e) {
        e.stopPropagation();
        sendReaderAction('highlight-delete', String(item.id != null ? item.id : index));
      });
      li.appendChild(del);
      li.addEventListener('click', function () {
        sendReaderAction('highlight-jump', String(item.id != null ? item.id : index));
      });
      list.appendChild(li);
    });
    if (!(items || []).length) {
      var empty = document.createElement('li');
      empty.textContent = '暂无高亮';
      list.appendChild(empty);
    }
  }
  function requestVocab() { sendReaderAction('vocab-request'); }
  function renderVocab(items) {
    var list = document.getElementById('appVocabList');
    if (!list) { return; }
    list.innerHTML = '';
    (items || []).forEach(function (item, index) {
      var li = document.createElement('li');
      var title = document.createElement('div');
      title.className = 'app-annotation-title';
      title.textContent = item.word || '';
      li.appendChild(title);
      if (item.translation) {
        var trans = document.createElement('div');
        trans.className = 'app-annotation-quote';
        trans.textContent = item.translation;
        li.appendChild(trans);
      }
      var meta = document.createElement('div');
      meta.className = 'app-annotation-meta';
      meta.textContent = String(item.time || '') + (item.position != null ? ' · 位置 ' + item.position : '');
      li.appendChild(meta);
      var del = document.createElement('button');
      del.type = 'button';
      del.className = 'app-annotation-delete';
      del.textContent = '×';
      del.title = '删除';
      del.addEventListener('click', function (e) {
        e.stopPropagation();
        sendReaderAction('vocab-delete', String(index));
      });
      li.appendChild(del);
      li.addEventListener('click', function () {
        sendReaderAction('vocab-jump', String(item.position || 0));
      });
      list.appendChild(li);
    });
    if (!(items || []).length) {
      var empty = document.createElement('li');
      empty.textContent = '暂无生词';
      list.appendChild(empty);
    }
  }
  function requestSpeech() { sendReaderAction('speech-request'); }
  function renderSpeechState(state) {
    state = state || {};
    var select = document.getElementById('appSpeechVoice');
    if (select) {
      var current = String(state.voice != null ? state.voice : select.value || '');
      select.innerHTML = '';
      var def = document.createElement('option');
      def.value = '';
      def.textContent = '选择语音';
      select.appendChild(def);
      (state.voices || []).forEach(function (voice) {
        var option = document.createElement('option');
        option.value = String(voice.value);
        option.textContent = voice.label;
        select.appendChild(option);
      });
      select.value = current;
    }
    var status = document.getElementById('appSpeechStatus');
    if (status) { status.textContent = state.status || ''; }
    var playbackBtn = document.getElementById('appSpeechToggle');
    if (playbackBtn) { playbackBtn.textContent = state.speaking ? '停止朗读' : '开始朗读'; }
    var rate = document.getElementById('appSpeechRate');
    if (rate && state.rate) { rate.value = String(state.rate); }
    var pitch = document.getElementById('appSpeechPitch');
    if (pitch && state.pitch) { pitch.value = String(state.pitch); }
  }
  function requestProgress() { sendReaderAction('progress-request'); }
  function renderProgress(state) {
    state = state || {};
    var pct = Number(state.percent || 0);
    var fill = document.getElementById('appProgressFill');
    if (fill) { fill.style.width = Math.max(0, Math.min(100, pct)) + '%'; }
    var meta = document.getElementById('appProgressMeta');
    if (meta) {
      meta.textContent = '当前 ' + pct.toFixed(1) + '%' +
        (state.syncEnabled ? ' · 同步已开启' : ' · 同步已关闭') +
        (state.lastSync ? ' · 上次同步 ' + state.lastSync : '');
    }
    var jump = document.getElementById('appProgressJump');
    if (jump && document.activeElement !== jump) { jump.value = pct.toFixed(1); }
    var toggle = document.getElementById('appProgressSyncToggle');
    if (toggle) { toggle.textContent = state.syncEnabled ? '关闭同步' : '开启同步'; }
    var syncToggle = document.getElementById('appSyncEnabledToggle');
    if (syncToggle) {
      syncToggle.textContent = state.syncEnabled ? '禁用' : '启用';
      syncToggle.classList.toggle('active', !!state.syncEnabled);
    }
    var setText = function (id, v, fallback) {
      var el = document.getElementById(id);
      if (el) { el.textContent = v || fallback || '—'; }
    };
    setText('appSyncStatusText', state.backendStatus, '未连接');
    setText('appSyncServerAddress', state.serverAddress, '—');
    setText('appSyncConnectionMode', state.connectionMode, '—');
    setText('appSyncLastTime', state.lastSync, '从未同步');
    var interval = document.getElementById('appSyncInterval');
    if (interval && state.syncInterval && document.activeElement !== interval) {
      interval.value = String(state.syncInterval);
    }
  }
  function requestViewState() { sendReaderAction('view-request'); }
  function appFullscreenEl() {
    return document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement || null;
  }
  function renderViewState(state) {
    state = state || {};
    var fullscreen = !!appFullscreenEl() || !!state.fullscreen;
    var focus = !!state.focus;
    var wide = !!state.wide;
    var setLabel = function (id, label, active) {
      var el = document.getElementById(id);
      if (el) {
        el.textContent = label;
        el.classList.toggle('active', !!active);
      }
    };
    setLabel('appFocusToggle', focus ? '退出专注模式' : '进入专注模式', focus);
    setLabel('appFullWidthToggle', wide ? '退出宽屏阅读' : '开启宽屏阅读', wide);
    setLabel('appFullscreenToggle', fullscreen ? '退出全屏' : '进入全屏', fullscreen);
    var meta = document.getElementById('appViewModeMeta');
    if (meta) {
      meta.textContent = '专注：' + (focus ? '开' : '关') + ' · 宽屏：' + (wide ? '开' : '关') + ' · 全屏：' + (fullscreen ? '开' : '关');
    }
  }
  function toggleAppFullscreen() {
    try {
      if (appFullscreenEl()) {
        var exit = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
        if (exit) { exit.call(document); }
      } else {
        var el = document.documentElement;
        var req = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen;
        if (req) { req.call(el); }
      }
    } catch (e) {}
    setTimeout(function () { renderViewState({}); }, 120);
  }
  function requestJumpState() { sendReaderAction('jump-request'); }
  function renderJumpState(state) {
    state = state || {};
    var pct = Number(state.percent || 0);
    var input = document.getElementById('appJumpInput');
    if (input && document.activeElement !== input) { input.value = pct.toFixed(2); }
    var meta = document.getElementById('appJumpMeta');
    if (meta) { meta.textContent = '当前位置 ' + pct.toFixed(2) + '%'; }
    var toggle = document.getElementById('appMinimapToggle');
    if (toggle) {
      toggle.textContent = state.minimapVisible ? '隐藏缩略图' : '显示缩略图';
      toggle.classList.toggle('active', !!state.minimapVisible);
    }
  }
  var appToastTimer = null;
  function showAppToast(text) {
    var toast = document.getElementById('appToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'appToast';
      document.getElementById('appReaderView').appendChild(toast);
    }
    toast.textContent = text;
    toast.hidden = false;
    clearTimeout(appToastTimer);
    appToastTimer = setTimeout(function () { toast.hidden = true; }, 3000);
  }
  function requestThemeState() { sendReaderAction('theme-request'); }
  function renderThemeState(state) {
    state = state || {};
    var select = document.getElementById('appThemeSelect');
    if (!select) { return; }
    var current = String(state.value != null ? state.value : select.value || '');
    select.innerHTML = '';
    (state.options || []).forEach(function (item) {
      var option = document.createElement('option');
      option.value = String(item.value);
      option.textContent = item.label;
      select.appendChild(option);
    });
    if (current) { select.value = current; }
  }
  function requestEncryptedState() { sendReaderAction('encrypted-request'); }
  function renderEncryptedState(state) {
    state = state || {};
    var btn = document.getElementById('appUnlockBtn');
    if (btn) { btn.hidden = !state.encrypted; }
    var meta = document.getElementById('appUnlockMeta');
    if (meta) { meta.textContent = state.message || (state.encrypted ? '本书已加密，请输入密码' : '本书未加密或已解锁'); }
  }
  var APP_PANEL_IDS = ['appReaderSettings', 'appSearchPanel', 'appTocPanel',
    'appBookmarkPanel', 'appNotePanel', 'appHighlightPanel', 'appVocabPanel',
    'appSpeechPanel', 'appProgressPanel', 'appViewModePanel', 'appJumpPanel', 'appUnlockPanel'];
  var syncIntervalEl = document.getElementById('appSyncInterval');
  if (syncIntervalEl) {
    syncIntervalEl.addEventListener('change', function () {
      sendReaderAction('progress-sync-interval', syncIntervalEl.value);
    });
  }
  function hideAllAppPanels() {
    APP_PANEL_IDS.forEach(function (id) {
      var panel = document.getElementById(id);
      if (panel) { panel.hidden = true; panel.setAttribute('aria-hidden', 'true'); }
    });
    var backdrop = document.getElementById('appPanelBackdrop');
    if (backdrop) { backdrop.hidden = true; }
  }
  function openAppPanel(id) {
    APP_PANEL_IDS.forEach(function (pid) {
      var panel = document.getElementById(pid);
      if (!panel) { return; }
      panel.hidden = pid !== id;
      panel.setAttribute('aria-hidden', pid === id ? 'false' : 'true');
    });
    var active = document.getElementById(id);
    var backdrop = document.getElementById('appPanelBackdrop');
    if (backdrop) { backdrop.hidden = false; }
    if (active) {
      active.setAttribute('role', 'dialog');
      active.setAttribute('aria-modal', 'true');
      setTimeout(function () {
        var focusable = active.querySelector('input:not([type="hidden"]), select, textarea, button');
        if (focusable) { try { focusable.focus(); } catch (e) {} }
      }, 0);
    }
  }
  function sendReaderAction(action, value) {
    var frame = document.getElementById('appReaderFrame');
    if (frame && frame.contentWindow) {
      frame.contentWindow.postMessage({ source: 'br-app-shell', action: action, value: value || '' }, '*');
    }
  }
  window.addEventListener('DOMContentLoaded', function () {
    var back = document.getElementById('appReaderBackBtn');
    if (back) { back.addEventListener('click', function () { showLibrary(true); }); }
    var backdrop = document.getElementById('appPanelBackdrop');
    if (backdrop) { backdrop.addEventListener('click', hideAllAppPanels); }
    ['fullscreenchange', 'webkitfullscreenchange', 'MSFullscreenChange'].forEach(function (evt) {
      document.addEventListener(evt, function () { renderViewState({}); });
    });
    document.addEventListener('click', function (e) {
      var readerView = document.getElementById('appReaderView');
      if (!readerView || !readerView.classList.contains('active')) { return; }
      if (!e.target || !e.target.closest) { return; }
      var btn = e.target.closest('button');
      if (!btn) { return; }
        var shellAction = btn.getAttribute('data-shell-action');
        if (shellAction && shellAction.indexOf('close') === 0) { hideAllAppPanels(); return; }
        if (shellAction === 'library') { showLibrary(true); return; }
        if (shellAction === 'settings') { openAppPanel('appReaderSettings'); requestThemeState(); return; }
        if (shellAction === 'editor') {
          hideAllAppPanels();
          showAppToast('正在打开编辑器…');
          sendReaderAction('editor');
          return;
        }
        if (shellAction === 'syncProgress') {
          /* 工具栏的「同步」= 旧版 manualSync()，把当前滚动进度 POST 到后端。 */
          showAppToast('正在同步阅读进度…');
          sendReaderAction('progress-sync-now');
          return;
        }
        if (shellAction === 'unlockPanel') {
          openAppPanel('appUnlockPanel');
          requestEncryptedState();
          return;
        }
        if (shellAction === 'unlockBook') {
          var unlockInput = document.getElementById('appUnlockInput');
          var pwd = unlockInput ? unlockInput.value : '';
          if (!pwd) { window.alert('请输入密码'); return; }
          sendReaderAction('unlock-book', pwd);
          return;
        }
        if (shellAction === 'toc') {
          openAppPanel('appTocPanel');
          requestToc();
          return;
        }
        if (shellAction === 'search') {
          openAppPanel('appSearchPanel');
          var appSearchInput = document.getElementById('appSearchInput');
          if (appSearchInput) { appSearchInput.focus(); }
          return;
        }
        if (shellAction === 'bookmarks') {
          openAppPanel('appBookmarkPanel');
          requestBookmarks();
          return;
        }
        if (shellAction === 'bookmarkAdd') {
          var bookmarkName = window.prompt('书签名称（可留空）:', '');
          if (bookmarkName !== null) { sendReaderAction('bookmark-add', bookmarkName); }
          return;
        }
        if (shellAction === 'notes') {
          openAppPanel('appNotePanel');
          requestNotes();
          return;
        }
        if (shellAction === 'noteAdd') {
          var appNoteInput = document.getElementById('appNoteInput');
          var noteText = appNoteInput ? appNoteInput.value.trim() : '';
          if (!noteText) { window.alert('请输入笔记内容'); return; }
          sendReaderAction('note-add', noteText);
          appNoteInput.value = '';
          return;
        }
        if (shellAction === 'highlights') {
          openAppPanel('appHighlightPanel');
          requestHighlights();
          return;
        }
        if (shellAction === 'highlightAdd') { sendReaderAction('highlight-add'); return; }
        if (shellAction === 'vocab') {
          openAppPanel('appVocabPanel');
          requestVocab();
          return;
        }
        if (shellAction === 'vocabAdd') {
          var vocabWord = document.getElementById('appVocabWord');
          var vocabTrans = document.getElementById('appVocabTranslation');
          var word = vocabWord ? vocabWord.value.trim() : '';
          if (!word) { window.alert('请输入生词'); return; }
          sendReaderAction('vocab-add', JSON.stringify({ word: word, translation: vocabTrans ? vocabTrans.value.trim() : '' }));
          vocabWord.value = '';
          if (vocabTrans) { vocabTrans.value = ''; }
          return;
        }
        if (shellAction === 'vocabSync') { requestVocab(); return; }
        if (shellAction === 'speech') {
          openAppPanel('appSpeechPanel');
          requestSpeech();
          return;
        }
        if (shellAction === 'speechToggle') { sendReaderAction('speech-toggle'); return; }
        if (shellAction === 'speechStop') { sendReaderAction('speech-stop'); return; }
        if (shellAction === 'progress') {
          openAppPanel('appProgressPanel');
          requestProgress();
          return;
        }
        if (shellAction === 'progressSave') { sendReaderAction('progress-save'); return; }
        if (shellAction === 'progressReload') { sendReaderAction('progress-reload'); return; }
        if (shellAction === 'progressSyncToggle') { sendReaderAction('progress-sync-toggle'); return; }
        if (shellAction === 'progressSyncSettings') {
          var syncBox = document.getElementById('appProgressSyncSettings');
          if (syncBox) { syncBox.hidden = !syncBox.hidden; }
          if (syncBox && !syncBox.hidden) { sendReaderAction('progress-sync-settings'); }
          return;
        }
        if (shellAction === 'progressSyncSettingsClose') {
          var syncBox2 = document.getElementById('appProgressSyncSettings');
          if (syncBox2) { syncBox2.hidden = true; }
          return;
        }
        if (shellAction === 'progressJump') {
          var progressJump = document.getElementById('appProgressJump');
          var pct = progressJump ? parseFloat(progressJump.value) : 0;
          if (!isFinite(pct)) { window.alert('请输入有效百分比'); return; }
          sendReaderAction('progress-jump', String(pct));
          return;
        }
        if (shellAction === 'viewMode') {
          openAppPanel('appViewModePanel');
          requestViewState();
          return;
        }
        if (shellAction === 'focusToggle') {
          sendReaderAction('focus');
          setTimeout(requestViewState, 120);
          return;
        }
        if (shellAction === 'fullWidthToggle') {
          sendReaderAction('fullWidth');
          setTimeout(requestViewState, 120);
          return;
        }
        if (shellAction === 'fullscreenToggle') { toggleAppFullscreen(); return; }
        if (shellAction === 'jumpPanel') {
          openAppPanel('appJumpPanel');
          requestJumpState();
          return;
        }
        if (shellAction === 'jumpTo') {
          var jumpInput = document.getElementById('appJumpInput');
          var pct2 = jumpInput ? parseFloat(jumpInput.value) : 0;
          if (!isFinite(pct2)) { window.alert('请输入有效百分比'); return; }
          sendReaderAction('jump-to', String(Math.max(0, Math.min(100, pct2))));
          setTimeout(requestJumpState, 350);
          return;
        }
        if (shellAction === 'jumpQuick') {
          sendReaderAction('jump-to', btn.getAttribute('data-value') || '0');
          setTimeout(requestJumpState, 350);
          return;
        }
        if (shellAction === 'minimapToggle') {
          sendReaderAction('minimap-toggle');
          setTimeout(requestJumpState, 150);
          return;
        }
        var action = btn.getAttribute('data-reader-action');
        if (action) { sendReaderAction(action, btn.getAttribute('data-value') || ''); }
    });
    var frame = document.getElementById('appReaderFrame');
    if (frame) {
      frame.addEventListener('load', function () {
        setTimeout(function () {
          requestToc();
          requestBookmarks();
          requestNotes();
          requestHighlights();
          requestVocab();
          requestSpeech();
          requestProgress();
          requestViewState();
          requestJumpState();
          requestThemeState();
          requestEncryptedState();
        }, 600);
      });
    }
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') { return; }
      hideAllAppPanels();
    });
    var tocSearch = document.getElementById('appTocSearch');
    if (tocSearch) {
      tocSearch.addEventListener('input', function () {
        var q = tocSearch.value.trim().toLowerCase();
        var list = document.getElementById('appTocList');
        if (!list) { return; }
        Array.prototype.forEach.call(list.children, function (li) {
          li.style.display = li.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
        });
      });
    }
    var appSearchInput = document.getElementById('appSearchInput');
    if (appSearchInput) {
      var searchTimer = null;
      appSearchInput.addEventListener('input', function () {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(function () {
          sendReaderAction('search-run', appSearchInput.value);
        }, 250);
      });
    }
    var appSpeechVoice = document.getElementById('appSpeechVoice');
    if (appSpeechVoice) {
      appSpeechVoice.addEventListener('change', function () {
        sendReaderAction('speech-voice', appSpeechVoice.value);
      });
    }
    var appSpeechRate = document.getElementById('appSpeechRate');
    if (appSpeechRate) {
      appSpeechRate.addEventListener('input', function () {
        sendReaderAction('speech-rate', appSpeechRate.value);
      });
    }
    var appSpeechPitch = document.getElementById('appSpeechPitch');
    if (appSpeechPitch) {
      appSpeechPitch.addEventListener('input', function () {
        sendReaderAction('speech-pitch', appSpeechPitch.value);
      });
    }
    var appThemeSelect = document.getElementById('appThemeSelect');
    if (appThemeSelect) {
      appThemeSelect.addEventListener('change', function () {
        sendReaderAction('theme', appThemeSelect.value);
      });
    }
  });
  window.addEventListener('message', function (ev) {
    var d = ev && ev.data;
    if (!d || d.source !== 'br-reader') { return; }
    if (d.type === 'toc') { renderToc(d.items || []); }
    if (d.type === 'search-results') { renderSearchResults(d.items || []); }
    if (d.type === 'bookmarks') { renderBookmarks(d.items || []); }
    if (d.type === 'notes') { renderNotes(d.items || []); }
    if (d.type === 'highlights') { renderHighlights(d.items || []); }
    if (d.type === 'vocab') { renderVocab(d.items || []); }
    if (d.type === 'speech-state') { renderSpeechState(d.state || {}); }
    if (d.type === 'progress-state') { renderProgress(d.state || {}); }
    if (d.type === 'view-state') { renderViewState(d.state || {}); }
    if (d.type === 'jump-state') { renderJumpState(d.state || {}); }
    if (d.type === 'theme-state') { renderThemeState(d.state || {}); }
    if (d.type === 'editor-state') {
      showAppToast(d.message || (d.available ? '编辑器已打开' : '编辑器入口不可用，请重新打开本书'));
    }
    if (d.type === 'encrypted-state') { renderEncryptedState(d.state || {}); }
    if (d.type === 'go-library') { showLibrary(true); }
  });
  window.BRAppReaderToolbar = {
    send: sendReaderAction,
    requestToc: requestToc,
    renderToc: renderToc,
    requestBookmarks: requestBookmarks,
    renderBookmarks: renderBookmarks,
    requestNotes: requestNotes,
    renderNotes: renderNotes,
    requestHighlights: requestHighlights,
    renderHighlights: renderHighlights,
    requestVocab: requestVocab,
    renderVocab: renderVocab,
    requestSpeech: requestSpeech,
    renderSpeechState: renderSpeechState,
    requestProgress: requestProgress,
    renderProgress: renderProgress,
    requestViewState: requestViewState,
    renderViewState: renderViewState,
    toggleAppFullscreen: toggleAppFullscreen,
    requestJumpState: requestJumpState,
    renderJumpState: renderJumpState,
    requestThemeState: requestThemeState,
    renderThemeState: renderThemeState,
    requestEncryptedState: requestEncryptedState,
    renderEncryptedState: renderEncryptedState
  };
  window.BRAppRouter = {
    showLibrary: showLibrary,
    showReader: showReader,
    start: start,
    current: function () { return current; }
  };
})();
"""

# 标签页伪装：切到其他标签时把标题改成 innocuous 的“百度一下”，切回来还原。
# 与旧阅读页 browser_reader.py 的 title_change_script 行为一致；统一壳（书库页 /
# 阅读视图）本身也需要，否则从书库标签切走时标题仍暴露“书库”。
TITLE_GUARD_JS = r"""
(function () {
  'use strict';
  var HIDDEN_TITLE = '百度一下，你就知道';
  var realTitle = document.title || '';
  function apply() {
    try {
      if (document.hidden) { document.title = HIDDEN_TITLE; }
      else { document.title = realTitle; }
    } catch (e) {}
  }
  /* 只用 visibilitychange + document.hidden 判断“切换标签/最小化”。
     不要用 blur 兜底：点击页面内的 iframe 阅读区时顶层 window 也会 blur，
     会把仍可见页面的标题误改成“百度一下”。 */
  document.addEventListener('visibilitychange', apply);
  apply();
})();
"""

_PORTAL_TEMPLATE = r"""<!DOCTYPE html>
<html lang="__LANG__">
<head>
<meta charset="UTF-8">
__STARTUP_GATE_EARLY__
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#2f7cf6">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>__PORTAL_TITLE__</title>
<link rel="manifest" href="/manifest.webmanifest">
<style>
:root{--br-page-bg:#f5f6f8;--br-page-fg:#222;--br-card-bg:#fff;--br-nav-border:#e3e5e9}
*{box-sizing:border-box}
body{margin:0;background:var(--br-page-bg);color:var(--br-page-fg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased}
button,input,select{font-family:inherit}
__RESPONSIVE_CSS__
__PORTAL_CSS__
__STARTUP_GATE_CSS__
__SCROLL_NAV_CSS__
__APP_SHELL_CSS__
</style>
</head>
<body>
<div id="brLoadingMask" role="status" aria-live="polite">
  <div class="br-loading-card">
    <div class="br-loading-spinner" aria-hidden="true"></div>
    <div class="br-loading-text" id="brLoadingText">__PORTAL_LOADING__…</div>
  </div>
</div>
<div id="appLibraryView" class="app-view active">
<div class="br-portal" id="portalRoot">
  <header class="br-portal-hero">
    <div class="br-portal-hero-main">
      <div class="br-portal-brand">
        <span class="br-portal-logo" aria-hidden="true">N</span>
        <div class="br-portal-brand-text">
          <h1>__PORTAL_TITLE__</h1>
          <p>__PORTAL_TAGLINE__</p>
        </div>
      </div>
      <div class="br-portal-hero-actions">
        <span class="br-net-badge offline" id="netBadge">__OFFLINE__</span>
        <button type="button" id="refreshBtn" class="br-portal-icon-btn" title="__PORTAL_REFRESH__" aria-label="__PORTAL_REFRESH__">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 5.6"/><path d="M20 4v7h-7"/></svg>
          <span>__PORTAL_REFRESH__</span>
        </button>
        <button type="button" id="uploadBtn" class="br-portal-icon-btn" title="__PORTAL_UPLOAD__" aria-label="__PORTAL_UPLOAD__">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 16V4M6 10l6-6 6 6"/><path d="M4 18v2h16v-2"/></svg>
          <span>__PORTAL_UPLOAD__</span>
        </button>
        <input type="file" id="uploadInput" accept=".txt,.md,.html,.htm,.epub,.pdf,.mobi,.azw,.azw3" multiple hidden>
        <button type="button" id="portalSettingsBtn" class="br-portal-icon-btn br-portal-settings-btn" title="__PORTAL_SETTINGS__" aria-label="__PORTAL_SETTINGS__">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg>
          <span>__PORTAL_SETTINGS__</span>
        </button>
      </div>
    </div>
    <div class="br-portal-hero-foot">
      <span class="br-portal-count" id="bookCount">__PORTAL_COUNT__</span>
      <span class="br-portal-divider" aria-hidden="true"></span>
      <span id="tip"></span>
    </div>
  </header>

  <div class="br-portal-controls">
    <div class="br-search-wrap">
      <svg class="br-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg>
      <input type="search" id="searchInput" placeholder="__PORTAL_SEARCH__">
    </div>
    <div class="br-portal-tabs" role="tablist">
      <button type="button" id="tabHistory" class="br-portal-tab" role="tab">__PORTAL_HISTORY__</button>
      <button type="button" id="tabLocal" class="br-portal-tab" role="tab">__PORTAL_LOCAL_BOOKS__</button>
      <button type="button" id="tabNetwork" class="br-portal-tab active" role="tab">__PORTAL_NETWORK_BOOKS__</button>
      <button type="button" id="manageLocalBtn" class="br-portal-tab br-manage-local-btn" role="button" title="__PORTAL_MANAGE_LOCAL__">__PORTAL_MANAGE_LOCAL__</button>
    </div>
    <div class="br-local-manage-bar" id="localManageBar" style="display:none">
      <label class="br-local-select-all"><input type="checkbox" id="localSelectAll"> __PORTAL_SELECT_ALL__</label>
      <button type="button" id="localDeleteSelected" class="br-local-danger">__PORTAL_DELETE_SELECTED__</button>
      <button type="button" id="localDeleteAll" class="br-local-danger">__PORTAL_DELETE_ALL__</button>
      <button type="button" id="localManageExit">__PORTAL_CANCEL__</button>
    </div>
  </div>

  <div class="book-grid" id="bookGrid"></div>
  <div class="br-portal-empty" id="empty" style="display:none"></div>
  <nav class="br-portal-pager" id="pager" aria-label="__PORTAL_PAGE_LABEL__" style="display:none">
    <button type="button" id="prevPage" class="br-pager-btn" aria-label="__PORTAL_PREV__" title="__PORTAL_PREV__">&#8249;</button>
    <div class="br-pager-numbers" id="pageNumbers"></div>
    <button type="button" id="nextPage" class="br-pager-btn" aria-label="__PORTAL_NEXT__" title="__PORTAL_NEXT__">&#8250;</button>
    <span class="br-pager-info" id="pageInfo"></span>
  </nav>
</div>

<nav class="br-mobile-nav br-portal-nav" id="brMobileNav">
  <button type="button" data-nav="library" class="active"><span class="br-nav-icon">&#128218;</span><span>__LIBRARY__</span></button>
  <button type="button" data-nav="offline"><span class="br-nav-icon">&#128190;</span><span>__PORTAL_OFFLINE_BOOKS__</span></button>
  <button type="button" data-nav="settings"><span class="br-nav-icon">&#9881;</span><span>__PORTAL_SETTINGS__</span></button>
</nav>

<section class="br-settings-view" id="brSettingsView">
  <div class="br-settings-head">
    <button type="button" id="settingsBack">&#8592;</button>
    <h2>__PORTAL_SETTINGS__</h2>
    <span class="br-net-badge offline" id="settingsNet">__OFFLINE__</span>
  </div>
  <div class="br-settings-group">
    <h3>__NETWORK__</h3>
    <div class="br-setting-row"><label for="backendInput">__BACKEND__</label><input type="text" id="backendInput" autocomplete="off"></div>
    <div class="br-setting-row"><label for="keyInput">__API_KEY__</label><input type="password" id="keyInput" autocomplete="off"></div>
    <div class="br-setting-actions">
      <button type="button" class="primary" id="saveConnBtn">__SAVE__</button>
      <button type="button" id="clearCacheBtn">__PORTAL_CLEAR_CACHE__</button>
    </div>
    <p style="font-size:12px;opacity:.65;margin:10px 0 0">__OFFLINE_HINT__</p>
  </div>
  <div class="br-settings-group">
    <h3>__APPEARANCE__</h3>
    <div class="br-setting-row"><label for="fontSizeInput">__FONT_SIZE__</label><input type="range" id="fontSizeInput" min="12" max="32" value="18"><span class="br-value" id="fontSizeValue">18</span></div>
    <div class="br-setting-row"><label for="lineHeightInput">__LINE_HEIGHT__</label><input type="range" id="lineHeightInput" min="12" max="28" value="18"><span class="br-value" id="lineHeightValue">1.8</span></div>
    <div class="br-setting-row"><label for="darkInput">__NIGHT_MODE__</label><input type="checkbox" id="darkInput" style="min-width:24px;min-height:24px"></div>
  </div>
</section>

<div class="br-portal-offline-reader" id="offlineReader">
  <div class="br-offline-toolbar" id="offlineToolbar" aria-label="本地书阅读工具栏">
    <button type="button" id="offlineBack" title="返回书库">&#8592;</button>
    <strong class="br-offline-title" id="offlineTitle"></strong>
    <button type="button" data-offline-action="fontDown" title="缩小字号">A-</button>
    <button type="button" data-offline-action="fontUp" title="放大字号">A+</button>
    <button type="button" data-offline-action="lineDown" title="减小行高">行高-</button>
    <button type="button" data-offline-action="lineUp" title="增大行高">行高+</button>
    <button type="button" data-offline-action="night" title="夜间模式">夜间</button>
    <button type="button" data-offline-action="top" title="回到顶部">顶部</button>
    <button type="button" data-offline-action="bottom" title="去到底部">底部</button>
  </div>
  <div class="br-offline-body" id="offlineBody"></div>
</div>
</div><!-- /appLibraryView -->

<div id="appReaderView" class="app-view">
  <div id="appPanelBackdrop" hidden aria-hidden="true"></div>
  <button type="button" id="appReaderBackBtn" title="返回书库 / Library">&#8592; 书库</button>
  <div class="br-app-toolbar" id="appReaderToolbar" aria-label="阅读工具栏">
    <button type="button" data-shell-action="library" title="书库">书库</button>
    <button type="button" data-shell-action="toc" title="目录">目录</button>
    <button type="button" data-shell-action="search" title="搜索">搜索</button>
    <button type="button" data-shell-action="bookmarks" title="书签">书签</button>
    <button type="button" data-shell-action="notes" title="笔记">笔记</button>
    <button type="button" data-shell-action="highlights" title="高亮">高亮</button>
    <button type="button" data-shell-action="vocab" title="生词">生词</button>
    <button type="button" data-shell-action="speech" title="朗读">朗读</button>
    <button type="button" data-shell-action="progress" title="进度">进度</button>
    <button type="button" data-shell-action="jumpPanel" title="位置跳转">跳转</button>
    <button type="button" data-shell-action="editor" title="浏览器编辑">编辑</button>
    <button type="button" data-shell-action="syncProgress" title="同步阅读进度">同步</button>
    <button type="button" id="appUnlockBtn" data-shell-action="unlockPanel" title="解锁加密书" hidden>解锁</button>
    <button type="button" data-reader-action="fontDown" title="缩小字号">A-</button>
    <button type="button" data-reader-action="fontUp" title="放大字号">A+</button>
    <button type="button" data-reader-action="settings" title="设置">设置</button>
    <button type="button" data-reader-action="top" title="顶部">顶部</button>
    <button type="button" data-reader-action="bottom" title="底部">底部</button>
    <button type="button" data-shell-action="viewMode" title="阅读模式">模式</button>
    <button type="button" data-reader-action="focus" title="专注模式">专注</button>
    <button type="button" data-reader-action="fullscreen" title="全屏">全屏</button>
    <button type="button" data-shell-action="settings" title="更多设置">设置+</button>
  </div>
  <div class="br-app-settings" id="appReaderSettings" hidden>
    <h3>阅读设置</h3>
    <div class="br-app-setting-row">
      <button type="button" data-reader-action="fontDown">A-</button>
      <button type="button" data-reader-action="fontUp">A+</button>
      <button type="button" data-reader-action="lineDown">行高-</button>
      <button type="button" data-reader-action="lineUp">行高+</button>
    </div>
    <div>主题：<select id="appThemeSelect"></select></div>
    <div class="br-app-setting-row">
      <button type="button" data-reader-action="themeManager">主题管理</button>
      <button type="button" data-reader-action="settings">字体设置</button>
      <button type="button" data-reader-action="fullWidth">宽屏阅读</button>
      <button type="button" data-reader-action="legacyToolbar">旧版工具栏</button>
    </div>
    <div class="br-app-setting-row">
      <button type="button" data-reader-action="downloadTxt">下载 TXT</button>
      <button type="button" data-reader-action="print">打印 / PDF</button>
      <button type="button" data-shell-action="editor">浏览器编辑</button>
    </div>
    <div class="br-app-setting-row">
      <button type="button" data-reader-action="autoScrollPanel">自动滚动</button>
      <button type="button" data-reader-action="paginationSettings">翻页设置</button>
      <button type="button" data-shell-action="closeSettings">关闭</button>
    </div>
  </div>
  <div class="br-app-settings" id="appSearchPanel" hidden>
    <h3>内容搜索</h3>
    <input type="search" id="appSearchInput" placeholder="输入关键词后自动搜索">
    <ul id="appSearchList"></ul>
    <div class="br-app-setting-row">
      <button type="button" data-reader-action="searchNext">下一个</button>
      <button type="button" data-shell-action="closeSearch">关闭</button>
    </div>
  </div>
  <div class="br-app-settings" id="appUnlockPanel" hidden>
    <h3>解锁加密书</h3>
    <div id="appUnlockMeta">本书未加密或已解锁</div>
    <input type="password" id="appUnlockInput" placeholder="请输入书籍密码" autocomplete="off">
    <div class="br-app-setting-row">
      <button type="button" data-shell-action="unlockBook">解锁</button>
      <button type="button" data-shell-action="closeUnlock">关闭</button>
    </div>
  </div>
  <div class="br-app-settings" id="appJumpPanel" hidden>
    <h3>位置跳转</h3>
    <div id="appJumpMeta">当前位置 0.00%</div>
    <input type="number" id="appJumpInput" min="0" max="100" step="0.01" placeholder="输入 0-100 的百分比">
    <div class="br-app-setting-row">
      <button type="button" data-shell-action="jumpTo">跳转</button>
      <button type="button" data-shell-action="jumpQuick" data-value="25">25%</button>
      <button type="button" data-shell-action="jumpQuick" data-value="50">50%</button>
      <button type="button" data-shell-action="jumpQuick" data-value="75">75%</button>
      <button type="button" id="appMinimapToggle" data-shell-action="minimapToggle">显示缩略图</button>
      <button type="button" data-shell-action="closeJump">关闭</button>
    </div>
  </div>
  <div class="br-app-settings" id="appViewModePanel" hidden>
    <h3>阅读模式</h3>
    <div id="appViewModeMeta">专注：关 · 宽屏：关 · 全屏：关</div>
    <div class="br-app-setting-row">
      <button type="button" id="appFocusToggle" data-shell-action="focusToggle">进入专注模式</button>
      <button type="button" id="appFullWidthToggle" data-shell-action="fullWidthToggle">开启宽屏阅读</button>
      <button type="button" id="appFullscreenToggle" data-shell-action="fullscreenToggle">进入全屏</button>
      <button type="button" data-shell-action="closeViewMode">关闭</button>
    </div>
  </div>
  <div class="br-app-settings" id="appProgressPanel" hidden>
    <h3>阅读进度</h3>
    <div id="appProgressTrack"><div id="appProgressFill"></div></div>
    <div id="appProgressMeta">当前 0%</div>
    <input type="number" id="appProgressJump" min="0" max="100" step="0.1" placeholder="跳转到百分比，例如 50">
    <div class="br-app-setting-row">
      <button type="button" data-shell-action="progressJump">跳转</button>
      <button type="button" data-shell-action="progressSave">保存当前进度</button>
      <button type="button" data-shell-action="progressReload">恢复进度</button>
      <button type="button" data-shell-action="progressSyncSettings">进度同步设置</button>
      <button type="button" id="appProgressSyncToggle" data-shell-action="progressSyncToggle">开启同步</button>
      <button type="button" data-shell-action="closeProgress">关闭</button>
    </div>
    <div class="br-app-progress-sync-settings" id="appProgressSyncSettings" hidden>
      <div class="br-app-setting-line"><span>启用进度同步</span><button type="button" id="appSyncEnabledToggle" data-shell-action="progressSyncToggle">禁用</button></div>
      <div class="br-app-setting-line"><span>同步状态</span><span id="appSyncStatusText">未连接</span></div>
      <div class="br-app-setting-line"><span>服务器地址</span><span id="appSyncServerAddress">检测中…</span></div>
      <div class="br-app-setting-line"><span>连接模式</span><span id="appSyncConnectionMode">检测中…</span></div>
      <div class="br-app-setting-line"><span>上次同步时间</span><span id="appSyncLastTime">从未同步</span></div>
      <div class="br-app-setting-line">
        <span>自动同步间隔</span>
        <select id="appSyncInterval">
          <option value="300000">5 分钟</option>
          <option value="600000">10 分钟</option>
          <option value="1800000">30 分钟</option>
          <option value="3600000">1 小时</option>
          <option value="7200000">2 小时</option>
        </select>
      </div>
      <div class="br-app-setting-row">
        <button type="button" data-shell-action="syncProgress">立即同步</button>
        <button type="button" data-shell-action="progressSyncSettingsClose">关闭</button>
      </div>
    </div>
  </div>
  <div class="br-app-settings" id="appSpeechPanel" hidden>
    <h3>朗读</h3>
    <select id="appSpeechVoice"><option value="">选择语音</option></select>
    <div class="br-app-setting-row">
      <button type="button" id="appSpeechToggle" data-shell-action="speechToggle">开始朗读</button>
      <button type="button" data-shell-action="speechStop">停止</button>
      <button type="button" data-shell-action="closeSpeech">关闭</button>
    </div>
    <label>语速 <input type="range" id="appSpeechRate" min="0.5" max="2" step="0.1" value="1"></label>
    <label>音调 <input type="range" id="appSpeechPitch" min="0.5" max="2" step="0.1" value="1"></label>
    <div id="appSpeechStatus"></div>
  </div>
  <div class="br-app-settings" id="appVocabPanel" hidden>
    <h3>生词本</h3>
    <input id="appVocabWord" placeholder="单词或短语">
    <input id="appVocabTranslation" placeholder="释义（可选）">
    <div class="br-app-setting-row">
      <button type="button" data-shell-action="vocabAdd">加入生词本</button>
      <button type="button" data-shell-action="vocabSync">同步单词本</button>
      <button type="button" data-shell-action="closeVocab">关闭</button>
    </div>
    <ul class="app-annotation-list" id="appVocabList"></ul>
  </div>
  <div class="br-app-settings" id="appHighlightPanel" hidden>
    <h3>高亮与标注</h3>
    <div class="br-app-setting-row">
      <button type="button" data-shell-action="highlightAdd">高亮当前选中文本</button>
      <button type="button" data-reader-action="highlightPrev">上一个</button>
      <button type="button" data-reader-action="highlightNext">下一个</button>
      <button type="button" data-shell-action="closeHighlights">关闭</button>
    </div>
    <ul class="app-annotation-list" id="appHighlightList"></ul>
  </div>
  <div class="br-app-settings" id="appBookmarkPanel" hidden>
    <h3>书签</h3>
    <div class="br-app-setting-row">
      <button type="button" data-shell-action="bookmarkAdd">添加当前位置书签</button>
      <button type="button" data-shell-action="closeBookmarks">关闭</button>
    </div>
    <ul class="app-annotation-list" id="appBookmarkList"></ul>
  </div>
  <div class="br-app-settings" id="appNotePanel" hidden>
    <h3>笔记</h3>
    <textarea id="appNoteInput" rows="3" placeholder="写下阅读想法"></textarea>
    <div class="br-app-setting-row">
      <button type="button" data-shell-action="noteAdd">添加笔记</button>
      <button type="button" data-shell-action="closeNotes">关闭</button>
    </div>
    <ul class="app-annotation-list" id="appNoteList"></ul>
  </div>
  <div class="br-app-settings" id="appTocPanel" hidden>
    <h3>章节目录</h3>
    <input type="search" id="appTocSearch" placeholder="搜索章节">
    <ul id="appTocList"></ul>
    <div class="br-app-setting-row">
      <button type="button" data-shell-action="closeToc">关闭</button>
    </div>
  </div>
  <iframe id="appReaderFrame" title="阅读器"></iframe>
</div>

<script>
__APP_RUNTIME_JS__
__DATA_SOURCE_JS__
__APP_ROUTER_JS__
window.__BR_LABELS__ = __LABELS_JSON__;
window.__BR_BOOT_SECRET__ = __SECRET_JSON__;
window.__BR_OFFLINE_MODE__ = __OFFLINE_MODE__;
window.__BR_OFFLINE_BOOKS__ = __OFFLINE_BOOKS_JSON__;
window.__BR_DEFAULT_BACKEND__ = __BACKEND_URL_JSON__;
__TITLE_GUARD_JS__
</script>
<script>
__PORTAL_JS__
</script>
__SCROLL_NAV_HTML__
<script>__SCROLL_NAV_JS__</script>
__STARTUP_GATE_HTML__
<script>__STARTUP_GATE_JS__</script>
</body>
</html>
"""

_PORTAL_JS = r"""
(function () {
    'use strict';
    var L = window.__BR_LABELS__ || {};
    /* 同一套书库 UI：网络模式走 API，离线模式使用生成页面时内嵌的书单 */
    var OFFLINE = window.__BR_OFFLINE_MODE__ === true;
    var OFFLINE_BOOKS = window.__BR_OFFLINE_BOOKS__ || [];
    var KEY_STORE = 'br_api_secret', BACK_STORE = 'br_backend_override';
    /* v2：旧缓存里含真实 path，整体弃用，避免继续在浏览器本地暴露目录。 */
    var CACHE_KEY = 'br_portal_books_v2', CACHE_TIME_KEY = 'br_portal_books_v2_synced_at';
    var DB_NAME = 'br_offline_books', STORE = 'books', INDEX_STORE = 'book_index';
    var PAGE_SIZE = 20;
    var mode = OFFLINE ? 'local' : 'network', books = [], offlineBooks = [], netOnline = false;
    var page = 1, total = 0, keyword = '', reqSeq = 0, searchTimer = null, syncing = false;
    /* 本地书籍管理模式：manageMode=true 时点卡片切换选中而非打开书 */
    var manageMode = false, selectedBooks = Object.create(null);

    function $(id) { return document.getElementById(id); }
    function setTip(text) { var el = $('tip'); if (el) { el.textContent = text || ''; } }
    function safe(fn) { try { return fn(); } catch (e) { return null; } }
    /* 后端公开标识固定为 20 位十六进制（book_identity.book_key_for_path）。
       旧版阅读页只注入 __BR_BOOK_FILE_PATH__、没注入 __BR_BOOK_KEY__ 时，
       IndexedDB 缓存会把书名当成 id；若不校验就拼 /reader?book=<书名>，
       后端必然返回「无法打开该书籍：文件不存在或不在书库中」。 */
    function isBackendBookKey(v) {
        return /^[0-9a-f]{20}$/i.test(String(v == null ? '' : v).trim());
    }
    /* 书库点书即记历史：阅读页自己写的历史在 file:// 书库 + http:// iframe 的跨源
       场景下会落进 iframe 的 localStorage，父页面读不到；简化面板更是完全不写。
       这里统一在本地书库侧落一条，保证离线/网络版都能在阅读历史里找到。 */
    function recordReadingHistory(b) {
        b = b || {};
        var bk = String(b.book_key || b.id || '');
        if (!bk) { return; }
        var ds = window.BRDataSource.local;
        var hist = ds.history().filter(function (x) {
            return String(x.bookId || x.id || '') !== bk;
        });
        hist.unshift({
            id: String(Date.now()),
            title: String(b.title || b.novel_title || b.name || bk),
            type: 'network', bookId: bk, readTime: Date.now(),
            reader_url: String(b.reader_url || '')
        });
        ds.saveHistory(hist.slice(0, 50));
    }
    var loadingTimer = null;
    function scheduleHideLoading(ms) {
        if (loadingTimer) { clearTimeout(loadingTimer); }
        loadingTimer = setTimeout(hideLoading, ms);
    }
    function showLoading(title) {
        var mask = $('brLoadingMask');
        if (!mask) { return; }
        var text = $('brLoadingText');
        if (text) {
            var prefix = L.portal_loading || '正在打开书籍';
            text.textContent = title ? (prefix + '《' + title + '》…') : (prefix + '…');
        }
        mask.style.display = 'flex';
        /* 兜底：后端异常或 iframe 始终不触发 load 时，不能把用户永久挡在遮罩后。 */
        scheduleHideLoading(15000);
    }
    function hideLoading() {
        if (loadingTimer) { clearTimeout(loadingTimer); loadingTimer = null; }
        var mask = $('brLoadingMask');
        if (mask) { mask.style.display = 'none'; }
    }
    function openWithFrame(opener) {
        var frame = document.getElementById('appReaderFrame');
        var before = frame ? String(frame.src || '') : '';
        opener();
        if (!frame) { scheduleHideLoading(300); return; }
        if (String(frame.src || '') !== before) {
            frame.addEventListener('load', hideLoading, { once: true });
        } else {
            /* 同一 src 重复点击不会再触发 load，短延时后收起遮罩。 */
            scheduleHideLoading(400);
        }
    }
    /* URL/密钥逻辑统一由 BRAppRuntime 提供，网络/离线差异不再散落在页面逻辑里 */
    function backend() { return window.BRAppRuntime.backend(); }
    function key() { return window.BRAppRuntime.key(); }
    function withKey(url) { return window.BRAppRuntime.withKey(url); }
    function headers() { return window.BRAppRuntime.apiHeaders(); }
    function paintNet() {
        ['netBadge', 'settingsNet'].forEach(function (id) {
            var el = $(id); if (!el) { return; }
            el.textContent = netOnline ? L.online : L.offline;
            el.className = 'br-net-badge ' + (netOnline ? 'online' : 'offline');
        });
        var tip = $('tip');
        if (tip) { tip.textContent = netOnline ? L.portal_online_tip : L.portal_offline_tip; }
    }
    function checkNet() {
        if (!backend()) { netOnline = false; paintNet(); return Promise.resolve(false); }
        return window.BRDataSource.http.health()
            .then(function (online) { netOnline = online; return online; })
            .catch(function () { netOnline = false; return false; })
            .then(function () { paintNet(); return netOnline; });
    }

    /* ---------- 数据层：服务端分页 + 服务端全库搜索 ----------
       旧版只请求 /api/books?page=1&page_size=200，再对这 200 本做前端过滤，
       书库超过 200 本时后面的书永远搜不到。现在每页固定 20 条，关键词交给
       后端 q（LIKE 全库 title/author/pinyin/tags/format/metadata/path），
       离线时对本地完整书单做同样的过滤与分页。 */
    function keywordOf() {
        return (($('searchInput') || {}).value || '').trim();
    }
    function pickItems(d) {
        if (Array.isArray(d)) { return d; }
        if (!d) { return []; }
        var candidates = [d.items, d.results, d.data];
        for (var i = 0; i < candidates.length; i++) {
            if (Array.isArray(candidates[i])) { return candidates[i]; }
            if (candidates[i] && Array.isArray(candidates[i].items)) { return candidates[i].items; }
        }
        return [];
    }
    function cachedBooks() {
        return safe(function () { return JSON.parse(localStorage.getItem(CACHE_KEY) || '[]'); }) || [];
    }
    function matchLocal(b, kw) {
        if (!kw) { return true; }
        var hay = [b.title, b.novel_title, b.name, b.book_name, b.author, b.pinyin, b.tags]
            .map(function (v) { return v == null ? '' : String(v); }).join(' ').toLowerCase();
        return hay.indexOf(kw.toLowerCase()) >= 0;
    }
    function sliceLocal(all) {
        var filtered = (all || []).filter(function (b) { return matchLocal(b, keyword); });
        total = filtered.length;
        var pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
        if (page > pages) { page = pages; }
        return filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    }
    function slimBook(b) {
        /* 保留拼音/标签，让离线搜索与后端 q 的匹配范围尽量一致；
           metadata（章节正文）体积过大，不写入 localStorage。 */
        return {
            book_key: b.book_key || '', book_id: b.book_id || '',
            reader_url: b.reader_url || '',
            title: b.title || b.novel_title || b.name || '',
            author: b.author || '', format: b.format || '', status: b.status || '',
            pinyin: b.pinyin || '', tags: b.tags || ''
        };
    }
    function mergeCache(items) {
        if (!items || !items.length) { return; }
        safe(function () {
            var all = cachedBooks(), index = {};
            all.forEach(function (b, i) { index[String(b.book_key || b.title || i)] = i; });
            items.forEach(function (b) {
                var slim = slimBook(b), k = String(slim.book_key || slim.title);
                if (index[k] === undefined) { index[k] = all.length; all.push(slim); }
                else { all[index[k]] = slim; }
            });
            localStorage.setItem(CACHE_KEY, JSON.stringify(all));
        });
    }
    /* 后台一次拉取全量「精简书单」写入 IndexedDB：主列表仍是每页 20 条的
       服务端分页，这一步只保证后端关闭后离线书库/离线搜索覆盖全部书籍。
       走 /api/portal/books/index（后端只返回公开字段，不含 path/metadata），10 分钟节流；
       localStorage 只留少量「已浏览页」兜底，避免上万本书超出配额。 */
    function syncOfflineIndex() {
        if (syncing || !netOnline) { return; }
        var last = parseInt(safe(function () { return localStorage.getItem(CACHE_TIME_KEY); }) || '0', 10) || 0;
        if (Date.now() - last < 10 * 60 * 1000) { return; }
        syncing = true;
        window.BRDataSource.http.bookIndex()
            .then(function (d) {
                var items = pickItems(d);
                return items.length ? saveBookIndex(items.map(indexRecord)) : false;
            })
            .then(function (ok) {
                if (ok) { safe(function () { localStorage.setItem(CACHE_TIME_KEY, String(Date.now())); }); }
            })
            .catch(function () {})
            .then(function () { syncing = false; });
    }
    function renderOfflineFallback(seq) {
        return readBookIndex().then(function (list) {
            if (seq !== reqSeq) { return; }
            if (!list.length) { list = cachedBooks(); }
            /* 最后兜底：file:// 生成页内嵌的书单（离线生成时写入的真实服务端书） */
            if (!list.length && OFFLINE_BOOKS && OFFLINE_BOOKS.length) { list = OFFLINE_BOOKS.slice(); }
            render(sliceLocal(list), total);
        });
    }
    function loadBooks(targetPage) {
        if (typeof targetPage === 'number') { page = Math.max(1, targetPage); }
        keyword = keywordOf();
        var seq = ++reqSeq;
        if (mode === 'history') { return renderHistory(); }
        if (mode === 'local') { return loadLocalBooksView(); }
        /* 「网络书籍」列表始终以服务端为准：页面虽由 Python 以 file:// 生成、
           OFFLINE 标志为 true，但只要后端在线，就应显示真实服务端书库（book_key 正确），
           否则用户拿到的是生成时内嵌的旧书单/IndexedDB 缓存，book_key 与后端不符，
           点书拼 /reader?book=<key> 会报「书籍不存在」。仅后端不可达时才在
           checkNet 分支里降级到本地缓存。 */
        return checkNet().then(function (online) {
            if (!online) {
                netOnline = false; paintNet();
                return renderOfflineFallback(seq);
            }
            return window.BRDataSource.http.listBooks(page, PAGE_SIZE, keyword)
                .then(function (d) {
                    if (seq !== reqSeq) { return; }   /* 丢弃快速翻页/输入时的过期响应 */
                    var items = pickItems(d);
                    var n = parseInt(d && d.total, 10);
                    total = isNaN(n) ? items.length : n;
                    books = items;
                    mergeCache(items);
                    render(items, total);
                    syncOfflineIndex();
                })
                .catch(function () {
                    if (seq !== reqSeq) { return; }
                    netOnline = false; paintNet();
                    return renderOfflineFallback(seq);
                });
        });
    }

    /* ---------- 离线书籍：IndexedDB 中缓存的正文 ---------- */
    function openDB() {
        return new Promise(function (resolve, reject) {
            if (!window.indexedDB) { reject(new Error('no-idb')); return; }
            /* v3：旧 book_index 记录里带真实 path，升级时清空后从公开接口重建。 */
            var req = indexedDB.open(DB_NAME, 3);
            req.onupgradeneeded = function () {
                var db = req.result;
                if (!db.objectStoreNames.contains(STORE)) { db.createObjectStore(STORE, { keyPath: 'id' }); }
                if (!db.objectStoreNames.contains(INDEX_STORE)) { db.createObjectStore(INDEX_STORE, { keyPath: 'id' }); }
                else if (req.oldVersion < 3) {
                    try { req.transaction.objectStore(INDEX_STORE).clear(); } catch (e) {}
                }
            };
            req.onsuccess = function () { resolve(req.result); };
            req.onerror = function () { reject(req.error); };
        });
    }
    function indexRecord(b) {
        var s = slimBook(b);
        s.id = String(s.book_key || s.title || Math.random());
        return s;
    }
    function saveBookIndex(items) {
        return openDB().then(function (db) {
            return new Promise(function (resolve) {
                var tx = db.transaction(INDEX_STORE, 'readwrite');
                tx.objectStore(INDEX_STORE).put({ id: 'all', items: items });
                tx.oncomplete = function () { db.close(); resolve(true); };
                tx.onerror = function () { db.close(); resolve(false); };
            });
        }).catch(function () { return false; });
    }
    function readBookIndex() {
        return openDB().then(function (db) {
            return new Promise(function (resolve) {
                var tx = db.transaction(INDEX_STORE, 'readonly');
                var req = tx.objectStore(INDEX_STORE).get('all');
                req.onsuccess = function () { db.close(); resolve((req.result && req.result.items) || []); };
                req.onerror = function () { db.close(); resolve([]); };
            });
        }).catch(function () { return []; });
    }
    /* 本地书籍 = IndexedDB 中缓存/上传的书 + 离线页生成时内嵌的书 */
    function collectLocalBooks() {
        var embedded = (OFFLINE_BOOKS || []).map(function (b) {
            return {
                book_key: b.book_key || '', book_id: b.book_id || b.book_key || '',
                title: b.title || '', author: b.author || '', format: b.format || '',
                status: b.status || '', pinyin: b.pinyin || '', tags: b.tags || '',
                reader_url: b.reader_url || '', savedAt: 0, _blob: null
            };
        });
        return window.BRDataSource.local.listBooks().then(function (records) {
            var map = {};
            records.forEach(function (r) {
                var k = String(r.book_key || r.id || '');
                if (!k) { return; }
                map[k] = {
                    book_key: k, book_id: r.book_id || k,
                    title: r.title || k, author: r.author || '',
                    format: r.format || '', status: r.synced ? (L.synced || '已同步') : '',
                    pinyin: r.pinyin || '', tags: r.tags || '',
                    reader_url: r.reader_url || ('indexeddb:' + k),
                    savedAt: r.savedAt || 0, _blob: r.blob || null,
                    /* 只有 key 合法且 path 非空，后端才可能用 /reader?book= 打开。
                       旧缓存缺 __BR_BOOK_KEY__ 时 key 退化为书名（path 仍非空），
                       这类记录必须按纯本地书走简化面板，否则必然 404。 */
                    _hasPath: !!r.path && isBackendBookKey(k)
                };
            });
            embedded.forEach(function (b) {
                if (!b.book_key) { return; }
                if (!map[b.book_key]) { map[b.book_key] = b; return; }
                /* 生成页内嵌书单带真实的 file:// reader_url；IndexedDB 缓存记录常用
                   indexeddb: 占位符覆盖它，导致点书进「简化面板」而非 iframe 完整菜单。
                   只要内嵌书单里有真实 file:// url，就优先采用，保证菜单与网络版一致。 */
                var ref = String(b.reader_url || '');
                var cur = String(map[b.book_key].reader_url || '');
                if (ref.indexOf('file:') === 0 && cur.indexOf('file:') !== 0) {
                    map[b.book_key].reader_url = ref;
                }
            });
            return Object.keys(map).map(function (k) { return map[k]; })
                .sort(function (a, b) { return (b.savedAt || 0) - (a.savedAt || 0); });
        }).catch(function () { return embedded; });
    }
    function loadLocalBooksView() {
        return collectLocalBooks().then(function (list) {
            offlineBooks = list;
            render(sliceLocal(list), total);
        });
    }
    function renderHistory() {
        var history = window.BRDataSource.local.history();
        return collectLocalBooks().then(function (local) {
            var map = {};
            local.forEach(function (b) { map[b.book_key] = b; });
            var items = history.map(function (h) {
                var k = String(h.bookId || h.id || '');
                var b = map[k] || {};
                var ts = h.readTime || h.lastReadTime || 0;
                return {
                    book_key: k, book_id: b.book_id || k,
                    title: h.title || b.title || k, author: b.author || '',
                    format: b.format || '',
                    status: ts ? new Date(ts).toLocaleString() : '',
                    pinyin: b.pinyin || '', tags: b.tags || '',
                    reader_url: h.reader_url || b.reader_url || (b.book_key ? ('indexeddb:' + k) : ''), _blob: b._blob || null
                };
            });
            render(sliceLocal(items), total);
        });
    }

    function loadOfflineBooks() {
        return openDB().then(function (db) {
            return new Promise(function (resolve) {
                var tx = db.transaction(STORE, 'readonly');
                var req = tx.objectStore(STORE).getAll();
                req.onsuccess = function () { offlineBooks = req.result || []; db.close(); resolve(); };
                req.onerror = function () { offlineBooks = []; db.close(); resolve(); };
            });
        }).catch(function () { offlineBooks = []; }).then(function () {
            /* 只在离线标签页渲染；init 时预加载不得覆盖在线分页结果 */
            if (mode === 'offline') { render(sliceLocal(offlineBooks), total); }
        });
    }
    function openOfflineBook(id, b) {
        b = b || {};
        /* 依次尝试：新缓存主键(book_key)、旧缓存主键(book_id)。 */
        var candidates = [], seen = {};
        function addCandidate(v) {
            v = v == null ? '' : String(v);
            if (v && !seen[v]) { seen[v] = 1; candidates.push(v); }
        }
        addCandidate(b.book_key || id);
        addCandidate(b.book_id);
        addCandidate(id);
        return openDB().then(function (db) {
            return new Promise(function (resolve) {
                var tx = db.transaction(STORE, 'readonly');
                var store = tx.objectStore(STORE), found = null;
                candidates.forEach(function (key) {
                    var req = store.get(key);
                    req.onsuccess = function () { if (!found && req.result) { found = req.result; } };
                });
                tx.oncomplete = function () { db.close(); resolve(found); };
                tx.onerror = function () { db.close(); resolve(found); };
            });
        }).then(function (rec) {
            if (!rec) { hideLoading(); return; }
            /* 旧版本 cacheCurrentBook 用 document.title 存书名，标题伪装期间会把
               “百度一下，你就知道”写进 title；这里读取时兜底，避免显示伪装标题。 */
            var rawTitle = String(rec.title || '');
            var fake = /百度一下|百度一下[,，]你就知道/.test(rawTitle);
            /* 生成页内嵌书单 __BR_OFFLINE_BOOKS__ 的 title 是静态写入的，不受
               document.title 伪装污染；被污染的 IndexedDB 记录用这里的值纠正。 */
            var cleanTitle = '';
            try {
                var embedded = (window.__BR_OFFLINE_BOOKS__ || []).filter(function (x) {
                    return String(x.book_key || x.book_id) === String(id);
                })[0];
                if (embedded && embedded.title && !/百度一下/.test(String(embedded.title))) {
                    cleanTitle = String(embedded.title);
                }
            } catch (e) {}
            var bookTitle = (fake || !rawTitle)
                ? (cleanTitle || b.title || rec.book_id || rec.book_key || id || '书籍')
                : rawTitle;
            $('offlineTitle').textContent = bookTitle;
            $('offlineBody').innerHTML = rec.html || '';
            applyReaderSettings();
            $('offlineReader').classList.add('open');
            $('offlineReader').scrollTop = 0;
            $('portalRoot').style.display = 'none';
            /* 本地书面板是全屏层，portal 的全局滚动按钮(z-index 8000)会盖在其上。
               工具栏已提供「顶部/底部」，这里隐藏全局按钮避免孤立悬浮。 */
            var scrollNav = document.querySelector('.br-scroll-nav');
            if (scrollNav) { scrollNav.style.display = 'none'; }
            hideLoading();
        }).catch(function () { hideLoading(); });
    }

    function applyReaderSettings() {
        var s = safe(function () { return JSON.parse(localStorage.getItem('readerSettings') || '{}'); }) || {};
        var body = $('offlineBody');
        if (s.font_size) { body.style.fontSize = s.font_size + 'px'; }
        if (s.line_height) { body.style.lineHeight = s.line_height; }
        if (s.font_family) { body.style.fontFamily = s.font_family; }
    }

    /* 书库卡片：把书导出为 TXT 下载到本机/手机，脱离局域网后也能继续看 */
    function downloadBookTxt(book, title) {
        book = book || {};
        var bookKey = book.book_key || '';
        if (!bookKey) { alert(L.download_failed); return; }
        window.BRDataSource.http.downloadBook(bookKey)
            .then(function (res) {
                var a = document.createElement('a');
                var url = URL.createObjectURL(res.blob);
                var marker = "filename*=UTF-8''";
                var i = res.cd.indexOf(marker);
                var name = '';
                if (i >= 0) {
                    try { name = decodeURIComponent(res.cd.slice(i + marker.length).split(';')[0].trim()); } catch (e) {}
                }
                a.href = url;
                a.download = name || (String(title || 'book').replace(/[:*?"<>|]/g, '_') + '.txt');
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
            })
            .catch(function (e) { alert(L.download_failed + ': ' + e.message); });
    }

    /* 书名决定封面配色：同一本书在任何设备上颜色一致 */
    function coverTone(text) {
        var sum = 0;
        for (var i = 0; i < text.length; i++) { sum = (sum * 31 + text.charCodeAt(i)) % 1000003; }
        return sum % 6;
    }
    function makeCard(b) {
        var card = document.createElement('div');
        card.className = 'book-card';
        if (b.book_key) { card.setAttribute('data-book-key', b.book_key); }
        var title = String(b.title || b.novel_title || b.name || L.portal_title);

        /* 管理模式下的选择复选框（仅本地书籍 tab 可见，CSS 控制显隐） */
        var check = document.createElement('label');
        check.className = 'br-card-check';
        var checkBox = document.createElement('input');
        checkBox.type = 'checkbox';
        checkBox.className = 'br-card-checkbox';
        checkBox.checked = !!selectedBooks[b.book_key];
        checkBox.addEventListener('change', function () {
            if (checkBox.checked) { selectedBooks[b.book_key] = true; }
            else { delete selectedBooks[b.book_key]; }
            card.classList.toggle('selected', checkBox.checked);
        });
        check.appendChild(checkBox);

        var cover = document.createElement('div');
        cover.className = 'book-cover book-cover--' + coverTone(title);
        cover.setAttribute('aria-hidden', 'true');
        cover.textContent = (title.trim().charAt(0) || '书').toUpperCase();

        var meta = document.createElement('div');
        meta.className = 'book-meta';
        var h = document.createElement('h3');
        h.textContent = title;
        h.title = title;
        var author = document.createElement('p');
        author.className = 'book-author';
        author.textContent = b.author || (mode === 'local' ? L.portal_local_books : '—');
        meta.appendChild(h);
        meta.appendChild(author);

        var chips = document.createElement('div');
        chips.className = 'book-chips';
        [b.format, b.status].forEach(function (text) {
            if (!text) { return; }
            var chip = document.createElement('span');
            chip.className = 'book-chip';
            chip.textContent = text;
            chips.appendChild(chip);
        });
        if (mode === 'local') {
            var offlineChip = document.createElement('span');
            offlineChip.className = 'book-chip book-chip--offline';
            offlineChip.textContent = L.offline;
            chips.appendChild(offlineChip);
        }
        meta.appendChild(chips);

        var arrow = document.createElement('span');
        arrow.className = 'book-arrow';
        arrow.setAttribute('aria-hidden', 'true');
        arrow.textContent = '›';

        if (mode === 'network' && b.book_key) {
            var download = document.createElement('button');
            download.type = 'button';
            download.className = 'book-download';
            download.title = L.download_txt;
            download.textContent = L.download_txt || 'TXT';
            download.addEventListener('click', function (e) {
                e.stopPropagation();
                downloadBookTxt(b, title);
            });
            chips.appendChild(download);
        }
        if (mode === 'local' && b._blob) {
            var syncBtn = document.createElement('button');
            syncBtn.type = 'button';
            syncBtn.className = 'book-download';
            syncBtn.title = L.sync_to_backend;
            syncBtn.textContent = b.status ? L.synced : (L.sync_to_backend || '同步');
            syncBtn.disabled = !!b.status;
            syncBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                syncBookToBackend(b, title, syncBtn);
            });
            chips.appendChild(syncBtn);
        }

        card.appendChild(check);
        card.appendChild(cover);
        card.appendChild(meta);
        card.appendChild(arrow);
        if (manageMode && selectedBooks[b.book_key]) { card.classList.add('selected'); }
        card.addEventListener('click', function (e) {
            /* 管理模式：点卡片切换选中，不打开书 */
            if (manageMode) {
                if (e && e.target && e.target.tagName === 'INPUT') { return; }
                checkBox.checked = !checkBox.checked;
                checkBox.dispatchEvent(new Event('change'));
                return;
            }
            var ref = b.reader_url || '';
            showLoading(b.title || b.novel_title || b.name || '');
            recordReadingHistory(b);
            if (ref.indexOf('indexeddb:') === 0) {
                /* indexeddb: 有三种书，必须区分，否则会误走后端 iframe 报
                   「文件不存在或不在书库中」：
                   ① 服务端缓存书（_hasPath=true 且 key 为 20 位十六进制）：后端有它，
                      /reader?book=<key> 能动态生成完整阅读器，在线时优先走 iframe 完整菜单。
                   ② 旧缓存缺 __BR_BOOK_KEY__ 的书：key 退化成书名、path 可能非空，
                      后端无法按书名找书，只能用 #offlineReader 读 IndexedDB 正文。
                   ③ 纯浏览器上传书（_hasPath=false，正文只在 IndexedDB、后端没有）：
                      只能用 #offlineReader 简化面板，绝不能走后端 iframe。 */
                if (!b._hasPath || !isBackendBookKey(b.book_key)) { openOfflineBook(b.book_key, b); return; }
                var openFull = function () {
                    if (b.book_key && window.BRAppRouter) {
                        openWithFrame(function () { window.BRAppRouter.showReader(b.book_key, '', true); });
                    } else {
                        openOfflineBook(b.book_key, b);
                    }
                };
                var online = null;
                try { online = checkNet(); } catch (e) {}
                if (online && typeof online.then === 'function') {
                    online.then(function (ok) { if (ok) { openFull(); } else { openOfflineBook(b.book_key, b); } })
                           .catch(function () { openOfflineBook(b.book_key, b); });
                } else {
                    openOfflineBook(b.book_key, b);
                }
                return;
            }
            if (!window.BRAppRouter) {
                if (ref && ref.indexOf('file:') === 0) { location.href = ref; return; }
                if (b.book_key) { location.href = window.BRAppRuntime.readerUrl(b.book_key); return; }
                hideLoading(); return;
            }
            if (ref && ref.indexOf('file:') === 0) {
                openWithFrame(function () { window.BRAppRouter.showReader(b.book_key, ref, true); });
                return;
            }
            if (!b.book_key) { hideLoading(); return; }
            openWithFrame(function () { window.BRAppRouter.showReader(b.book_key, '', true); });
        });
        return card;
    }

    function pageWindow(current, pages) {
        /* 手机宽度放不下 7 个页码 + 两个箭头，会被 flex-wrap 挤成两行，
           因此窄屏用更紧凑的窗口，保证「上一页 / 页码 / 下一页」同一行。 */
        var compact = window.innerWidth <= 768;
        var maxNumbers = compact ? 5 : 7;
        var span = compact ? 0 : 1;
        var out = [], i;
        if (pages <= maxNumbers) { for (i = 1; i <= pages; i++) { out.push(i); } return out; }
        out.push(1);
        var start = Math.max(2, Math.min(pages - 1, current - span));
        var end = Math.min(pages - 1, Math.max(start, current + span));
        if (start > 2) { out.push('…'); }
        for (i = start; i <= end; i++) { out.push(i); }
        if (end < pages - 1) { out.push('…'); }
        out.push(pages);
        return out;
    }
    function renderPager(pages) {
        var pager = $('pager');
        if (!pager) { return; }
        pager.style.display = total > PAGE_SIZE ? 'flex' : 'none';
        var prev = $('prevPage'), next = $('nextPage');
        if (prev) { prev.disabled = page <= 1; }
        if (next) { next.disabled = page >= pages; }
        var info = $('pageInfo');
        if (info) {
            info.textContent = (L.portal_page || '%d / %d').replace('%d', page).replace('%d', pages);
        }
        var nums = $('pageNumbers');
        if (!nums) { return; }
        nums.innerHTML = '';
        pageWindow(page, pages).forEach(function (n) {
            if (n === '…') {
                var dots = document.createElement('span');
                dots.className = 'br-pager-ellipsis';
                dots.textContent = '…';
                nums.appendChild(dots);
                return;
            }
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'br-pager-num' + (n === page ? ' active' : '');
            btn.textContent = n;
            btn.addEventListener('click', function () { goPage(n); });
            nums.appendChild(btn);
        });
    }
    function goPage(n) {
        page = Math.max(1, n);
        loadBooks();
        safe(function () { window.scrollTo(0, 0); });
    }
    function render(items, totalArg) {
        var grid = $('bookGrid'), empty = $('empty');
        if (!grid) { return; }
        items = items || [];
        total = (typeof totalArg === 'number') ? totalArg : items.length;
        var pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
        if (page > pages) { page = pages; }
        grid.innerHTML = '';
        items.forEach(function (b) { grid.appendChild(makeCard(b)); });

        var count = $('bookCount');
        if (count) {
            var fmt = keyword ? (L.portal_found || '%d') : (L.portal_count || '%d');
            count.textContent = fmt.replace('%d', total);
        }
        if (empty) {
            empty.style.display = items.length ? 'none' : 'flex';
            empty.innerHTML = '';
            var icon = document.createElement('span');
            icon.className = 'br-portal-empty-icon';
            icon.textContent = '书';
            var text = document.createElement('span');
            text.className = 'br-portal-empty-text';
            text.textContent = keyword ? L.portal_no_match
                : (mode === 'offline' ? L.portal_no_offline : L.portal_empty);
            empty.appendChild(icon);
            empty.appendChild(text);
        }
        renderPager(pages);
    }

    function syncNav() {
        var current = mode === 'local' ? 'offline' : 'library';
        Array.prototype.forEach.call($('brMobileNav').querySelectorAll('button[data-nav]'), function (btn) {
            btn.classList.toggle('active', btn.getAttribute('data-nav') === current);
        });
    }

    /* ---------- 本地书籍管理：清理选中 / 全部清除 ---------- */
    function setManageMode(on) {
        manageMode = !!on;
        if (!manageMode) { selectedBooks = Object.create(null); }
        var portal = document.querySelector('.br-portal');
        var tabs = document.querySelector('.br-portal-tabs');
        var bar = $('localManageBar');
        if (portal) { portal.classList.toggle('manage-mode', manageMode); }
        if (tabs) { tabs.classList.toggle('manage-visible', mode === 'local' || mode === 'history'); }
        if (bar) { bar.style.display = manageMode ? 'flex' : 'none'; }
        loadBooks(1);
    }
    function deleteLocalBooks(keys, all) {
        var list = all ? null : Object.keys(keys || {}).filter(function (k) { return !!k; });
        if (!all && (!list || !list.length)) { setTip(L.portal_select_first || '请先选择书籍'); return; }
        var msg = all ? (L.portal_confirm_delete_all || '确定清除全部本地书籍？此操作不可恢复。')
                      : (L.portal_confirm_delete_selected || '确定删除选中的书籍？');
        if (!window.confirm(msg)) { return; }
        /* 主删除只操作 books store：book_index 在部分旧库并未创建，
           若与 books 放进同一 readwrite 事务，NotFoundError 会让整笔删除回滚。 */
        return window.BRDataSource.local.openDB().then(function (db) {
            return new Promise(function (resolve) {
                var tx = db.transaction(STORE, 'readwrite');
                var store = tx.objectStore(STORE);
                if (all) { store.clear(); }
                else { list.forEach(function (k) { store.delete(k); }); }
                tx.oncomplete = function () { resolve(true); };
                tx.onerror = function () { resolve(false); };
                tx.onabort = function () { resolve(false); };
            }).then(function (ok) { db.close(); return ok; });
        }).then(function (ok) {
            /* 网络书单索引是可选缓存：存在才清理，失败也不影响本地书删除结果。 */
            pruneLocalIndex(all, list);
            selectedBooks = Object.create(null);
            setManageMode(false);
            setTip(ok ? (L.portal_cleared || '已清除') : (L.upload_failed || '操作失败'));
        }).catch(function () { setTip(L.upload_failed || '操作失败'); });
    }
    function deleteHistoryBooks(keys, all) {
        var list = all ? null : Object.keys(keys || {}).filter(function (k) { return !!k; });
        if (!all && (!list || !list.length)) { setTip(L.portal_select_first || '请先选择书籍'); return; }
        var msg = all ? (L.portal_confirm_clear_history || '确定清除全部阅读历史？此操作不可恢复。')
                      : (L.portal_confirm_delete_history || '确定删除选中的阅读历史？');
        if (!window.confirm(msg)) { return; }
        var ds = window.BRDataSource.local;
        /* all=true 不依赖任何勾选，直接清空整份历史。 */
        var ok = all ? ds.clearHistory() : ds.deleteHistory(keys);
        selectedBooks = Object.create(null);
        setManageMode(false);
        setTip(ok ? (L.portal_cleared || '已清除') : (L.upload_failed || '操作失败'));
    }
    function pruneLocalIndex(all, list) {
        return openDB().then(function (db) {
            return new Promise(function (resolve) {
                if (!db.objectStoreNames.contains(INDEX_STORE)) { db.close(); resolve(); return; }
                var tx = db.transaction(INDEX_STORE, 'readwrite');
                var idx = tx.objectStore(INDEX_STORE);
                var g = idx.get('all');
                g.onsuccess = function () {
                    var data = g.result;
                    if (data && Array.isArray(data.items)) {
                        data.items = data.items.filter(function (it) {
                            if (all) { return false; }
                            var k = String(it.book_key || it.id || '');
                            return list.indexOf(k) < 0;
                        });
                        idx.put(data);
                    }
                };
                tx.oncomplete = function () { db.close(); resolve(); };
                tx.onerror = function () { db.close(); resolve(); };
                tx.onabort = function () { db.close(); resolve(); };
            });
        }).catch(function () {});
    }

    function setMode(m) {
        mode = m;
        page = 1;
        if (manageMode && m !== 'local' && m !== 'history') { setManageMode(false); }
        ['tabHistory', 'tabLocal', 'tabNetwork'].forEach(function (id) {
            var el = $(id);
            if (el) { el.classList.toggle('active', id === 'tab' + m.charAt(0).toUpperCase() + m.slice(1)); }
        });
        var tabs = document.querySelector('.br-portal-tabs');
        if (tabs) { tabs.classList.toggle('manage-visible', mode === 'local' || mode === 'history'); }
        syncNav();
        loadBooks(1);
    }

    function openSettings() {
        $('brSettingsView').classList.add('open');
        $('backendInput').value = backend();
        $('keyInput').value = key();
        var s = safe(function () { return JSON.parse(localStorage.getItem('readerSettings') || '{}'); }) || {};
        $('fontSizeInput').value = parseInt(s.font_size || 18, 10);
        $('fontSizeValue').textContent = $('fontSizeInput').value;
        $('lineHeightInput').value = Math.round(parseFloat(s.line_height || 1.8) * 10);
        $('lineHeightValue').textContent = parseFloat(s.line_height || 1.8).toFixed(1);
        $('darkInput').checked = document.documentElement.classList.contains('br-dark');
        location.hash = 'settings';
        checkNet();
    }
    function closeSettings() {
        $('brSettingsView').classList.remove('open');
        syncNav();
        if (location.hash === '#settings') { history.replaceState(null, '', location.pathname + '#library'); }
    }
    function saveSettings() {
        var s = safe(function () { return JSON.parse(localStorage.getItem('readerSettings') || '{}'); }) || {};
        s.font_size = $('fontSizeInput').value;
        s.line_height = (parseInt($('lineHeightInput').value, 10) / 10).toFixed(1);
        safe(function () { localStorage.setItem('readerSettings', JSON.stringify(s)); });
        document.documentElement.classList.toggle('br-dark', $('darkInput').checked);
        /* 离线阅读页若已打开，拖动滑块即时生效，不必退出后重新打开书籍 */
        applyReaderSettings();
    }

    /* ---------- 上传书籍：网络版写入服务端书库，离线版写入 IndexedDB ---------- */
    function randomBookKey() {
        var bytes = new Uint8Array(10);
        if (window.crypto && window.crypto.getRandomValues) { window.crypto.getRandomValues(bytes); }
        else { for (var i = 0; i < bytes.length; i++) { bytes[i] = Math.floor(Math.random() * 256); } }
        return Array.prototype.map.call(bytes, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
    }
    function escapeHtml(text) {
        return String(text == null ? '' : text)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
    function saveLocalBook(record) {
        return window.BRDataSource.local.saveBook(record);
    }
    function postBookBlob(blob, fileName, bookTitle) {
        return window.BRDataSource.http.uploadBook(blob, fileName, bookTitle)
            .then(function (d) {
                if (!d || !d.success) { throw new Error((d && d.error) || 'http'); }
                return d.book;
            });
    }
    /* 上传先入 IndexedDB：无论网络版还是离线版，书籍默认只在浏览器里。
       网络版可在本地书籍里点「同步到后端」单独上传到 Python 书架。 */
    function uploadToLocal(file) {
        return new Promise(function (resolve, reject) {
            var ext = (file.name.split('.').pop() || '').toLowerCase();
            var isText = (ext === 'txt' || ext === 'md');
            var reader = new FileReader();
            reader.onerror = function () { reject(new Error(L.upload_failed)); };
            reader.onload = function () {
                var k = randomBookKey();
                var title = file.name.replace(/\.[^.]+$/, '');
                var html = isText
                    ? '<h2>' + escapeHtml(title) + '</h2><pre style="white-space:pre-wrap;font:inherit">' +
                      escapeHtml(String(reader.result || '')) + '</pre>'
                    : '<h2>' + escapeHtml(title) + '</h2><p>' + escapeHtml(L.binary_local_hint || '该格式暂不支持浏览器内直接阅读，请先同步到后端。') + '</p>';
                saveLocalBook({
                    id: k, book_key: k, title: title, html: html,
                    path: '', format: ext.toUpperCase(), file_name: file.name,
                    blob: file, synced: false, savedAt: Date.now()
                }).then(function (ok) {
                    if (!ok) { reject(new Error(L.upload_failed)); return; }
                    OFFLINE_BOOKS.push({
                        book_key: k, book_id: k, title: title, author: '',
                        format: ext.toUpperCase(), tags: '', pinyin: '',
                        reader_url: 'indexeddb:' + k, savedAt: Date.now()
                    });
                    resolve(true);
                });
            };
            if (ext === 'txt' || ext === 'md') { reader.readAsText(file); }
            else { reader.readAsArrayBuffer(file); }
        });
    }
    function syncBookToBackend(b, title, btn) {
        var blob = b._blob || (b._record && b._record.blob);
        if (!blob) { alert(L.upload_failed + ': 原始文件不可用'); return; }
        if (btn) { btn.disabled = true; }
        setTip(L.sync_to_backend + '…');
        var fileName = (b._record && b._record.file_name) || (title || 'book') + '.' + (b.format || 'txt').toLowerCase();
        /* 先读完整记录再合并：book 列表对象只带 _blob、不带 html/blob/title 等原始字段。
           旧实现用 b._record || {} 合并，同步后只剩 id/book_key/synced，把 html 抹掉，
           导致本地书再次打开时内容页空白。这里以 IndexedDB 里的完整记录为准。 */
        window.BRDataSource.local.getBook(b.book_key).then(function (full) {
            return postBookBlob(blob, fileName, title || b.title).then(function () {
                var base = full || b._record || {};
                return saveLocalBook(Object.assign({}, base, {
                    id: b.book_key, book_key: b.book_key,
                    title: base.title || title || b.title,
                    blob: base.blob || blob,
                    html: base.html || '',
                    synced: true
                }));
            });
        }).then(function () {
            setMode('local');
            setTimeout(function () { setTip(L.synced); }, 80);
        }).catch(function (e) {
            var msg = L.upload_failed + ': ' + (e.message || e);
            setTip(msg);
            alert(msg);
            if (btn) { btn.disabled = false; }
        });
    }
    function uploadFiles(files) {
        if (!files || !files.length) { return; }
        var jobs = [];
        var uploadBtn = $('uploadBtn');
        if (uploadBtn) { uploadBtn.disabled = true; }
        setTip(L.portal_upload + '…');
        Array.prototype.forEach.call(files, function (f) {
            jobs.push(uploadToLocal(f).catch(function (e) {
                alert(L.upload_failed + ': ' + (e.message || e));
                return null;
            }));
        });
        Promise.all(jobs).then(function (results) {
            var ok = (results || []).filter(function (r) { return r; }).length;
            setMode('local');
            setTimeout(function () { setTip(L.upload_ok + ' ' + ok + '/' + files.length); }, 80);
        }).finally(function () {
            if (uploadBtn) { uploadBtn.disabled = false; }
        });
    }

    function bind() {
        $('refreshBtn').addEventListener('click', function () { loadBooks(1); });
        var uploadBtn = $('uploadBtn'), uploadInput = $('uploadInput');
        if (uploadBtn && uploadInput) {
            uploadBtn.addEventListener('click', function () { uploadInput.click(); });
            uploadInput.addEventListener('change', function () {
                uploadFiles(uploadInput.files);
                uploadInput.value = '';
            });
        }
        $('searchInput').addEventListener('input', function () {
            if (searchTimer) { clearTimeout(searchTimer); }
            searchTimer = setTimeout(function () { loadBooks(1); }, 250);
        });
        $('prevPage').addEventListener('click', function () { goPage(page - 1); });
        $('nextPage').addEventListener('click', function () { goPage(page + 1); });
        $('tabHistory').addEventListener('click', function () { setMode('history'); });
        $('tabLocal').addEventListener('click', function () { setMode('local'); });
        $('tabNetwork').addEventListener('click', function () { setMode('network'); });
        var manageBtn = $('manageLocalBtn');
        if (manageBtn) { manageBtn.addEventListener('click', function () { setManageMode(!manageMode); }); }
        var selectAll = $('localSelectAll');
        if (selectAll) {
            selectAll.addEventListener('change', function () {
                Array.prototype.forEach.call(document.querySelectorAll('#bookGrid .book-card'), function (card) {
                    var k = card.getAttribute('data-book-key');
                    if (!k) { return; }
                    var cb = card.querySelector('.br-card-checkbox');
                    if (!cb) { return; }
                    cb.checked = selectAll.checked;
                    cb.dispatchEvent(new Event('change'));
                });
            });
        }
        var delSel = $('localDeleteSelected');
        if (delSel) { delSel.addEventListener('click', function () {
            if (mode === 'history') { deleteHistoryBooks(selectedBooks, false); }
            else { deleteLocalBooks(selectedBooks, false); }
        }); }
        var delAll = $('localDeleteAll');
        if (delAll) { delAll.addEventListener('click', function () {
            if (mode === 'history') { deleteHistoryBooks(null, true); }
            else { deleteLocalBooks(null, true); }
        }); }
        var mngExit = $('localManageExit');
        if (mngExit) { mngExit.addEventListener('click', function () { setManageMode(false); }); }
        $('brMobileNav').addEventListener('click', function (e) {
            var btn = e.target.closest ? e.target.closest('button[data-nav]') : null;
            if (!btn) { return; }
            var which = btn.getAttribute('data-nav');
            Array.prototype.forEach.call($('brMobileNav').querySelectorAll('button'), function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            if (which === 'settings') { openSettings(); }
            else { closeSettings(); setMode(which === 'offline' ? 'local' : 'network'); }
        });
        $('settingsBack').addEventListener('click', closeSettings);
        var portalSettingsBtn = $('portalSettingsBtn');
        if (portalSettingsBtn) { portalSettingsBtn.addEventListener('click', openSettings); }
        window.addEventListener('hashchange', function () { if (location.hash !== '#settings') { closeSettings(); } });
        if (location.hash === '#settings') { openSettings(); }
        $('saveConnBtn').addEventListener('click', function () {
            var url = $('backendInput').value.trim().replace(/\/+$/, '');
            safe(function () {
                if (url) { localStorage.setItem(BACK_STORE, url); } else { localStorage.removeItem(BACK_STORE); }
                localStorage.setItem(KEY_STORE, $('keyInput').value || '');
            });
            loadBooks(1);
        });
        $('clearCacheBtn').addEventListener('click', function () {
            safe(function () {
                localStorage.removeItem(CACHE_KEY);
                localStorage.removeItem(CACHE_TIME_KEY);
            });
            openDB().then(function (db) {
                var tx = db.transaction([STORE, INDEX_STORE], 'readwrite');
                tx.objectStore(STORE).clear();
                tx.objectStore(INDEX_STORE).clear();
                tx.oncomplete = function () { db.close(); offlineBooks = []; loadBooks(1); };
            }).catch(function () {});
            if (window.caches) { caches.keys().then(function (ks) { ks.forEach(function (k) { caches.delete(k); }); }); }
            $('clearCacheBtn').textContent = L.portal_cleared;
        });
        $('fontSizeInput').addEventListener('input', function () { $('fontSizeValue').textContent = this.value; saveSettings(); });
        $('lineHeightInput').addEventListener('input', function () { $('lineHeightValue').textContent = (this.value / 10).toFixed(1); saveSettings(); });
        $('darkInput').addEventListener('change', saveSettings);
        function closeOfflineReader() {
            $('offlineReader').classList.remove('open');
            $('portalRoot').style.display = '';
            var scrollNav = document.querySelector('.br-scroll-nav');
            if (scrollNav) { scrollNav.style.display = ''; }
        }
        $('offlineBack').addEventListener('click', closeOfflineReader);
        $('offlineToolbar').addEventListener('click', function (e) {
            var btn = e.target && e.target.closest ? e.target.closest('button[data-offline-action]') : null;
            if (!btn) { return; }
            var action = btn.getAttribute('data-offline-action');
            if (action === 'library') { closeOfflineReader(); return; }
            if (action === 'top') { $('offlineReader').scrollTop = 0; return; }
            if (action === 'bottom') { var r = $('offlineReader'); r.scrollTop = r.scrollHeight; return; }
            if (action === 'fontDown' || action === 'fontUp') {
                var fi = $('fontSizeInput');
                fi.value = Math.max(12, Math.min(32, parseInt(fi.value, 10) + (action === 'fontUp' ? 2 : -2)));
                $('fontSizeValue').textContent = fi.value;
            } else if (action === 'lineDown' || action === 'lineUp') {
                var li = $('lineHeightInput');
                li.value = Math.max(12, Math.min(28, parseInt(li.value, 10) + (action === 'lineUp' ? 1 : -1)));
                $('lineHeightValue').textContent = (parseInt(li.value, 10) / 10).toFixed(1);
            } else if (action === 'night') {
                $('darkInput').checked = !$('darkInput').checked;
            }
            saveSettings();
        });
        setInterval(checkNet, 30000);
    }

    function init() {
        document.body.classList.add('br-web');
        /* 清掉 v1 书库缓存：里面保存过真实物理路径 */
        safe(function () {
            localStorage.removeItem('br_portal_books');
            localStorage.removeItem('br_portal_books_synced_at');
        });
        /* 先完成书库初始化（事件绑定 + 数据加载），再处理直达阅读路由。
           旧实现在 autoBook/start() 命中后直接 return，跳过了 bind()/loadBooks()，
           导致从阅读页返回书库时三个 tab 全空、必须整页刷新。初始化只渲染
           书库 DOM（bookGrid），与 reader 视图互不干扰，可安全提前。 */
        bind();
        paintNet();
        /* 立即探测后端并刷新在线徽章：netOnline 初始为 false，若只 paintNet 不 checkNet，
           页面刚打开会一直显示「离线」，要等 setInterval(checkNet,30000) 30 秒后才纠正。
           这会让后端明明在线时，从网络书籍 tab 点书被误判为离线、降级简化面板。 */
        checkNet();
        setMode(mode);
        loadOfflineBooks();
        if ('serviceWorker' in navigator && (location.protocol === 'http:' || location.protocol === 'https:')) {
            navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
        }
        /* 统一入口：?book=<公开标识> 直接进入统一 App Shell 的阅读视图。 */
        var autoBook = safe(function () { return new URLSearchParams(location.search).get('book') || ''; });
        if (autoBook && OFFLINE) {
            var target = OFFLINE_BOOKS.filter(function (b) { return b.book_key === autoBook; })[0];
            if (target && target.reader_url) {
                window.BRAppRouter.showReader(autoBook, target.reader_url, false);
                return;
            }
        }
        if (window.BRAppRouter && window.BRAppRouter.start()) { return; }
        if (autoBook && window.BRAppRouter) {
            window.BRAppRouter.showReader(autoBook, '', false);
            return;
        }
    }
    if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); } else { init(); }
})();
"""


def build_portal_html(locale: Optional[str] = None, secret: str = "",
                      startup_password_enabled: bool = False,
                      startup_password: str = "",
                      offline_books: Optional[list] = None,
                      backend_url: str = "") -> str:
    """生成局域网书库入口页（在线 / 离线共用同一页面）。

    Args:
        locale: 界面语言；None 时读取全局 i18n。
        secret: 后端接口密钥，仅作为首次访问的默认值写入页面（之后由 localStorage 覆盖）。
        startup_password_enabled: 是否开启浏览器阅读器开屏密码。
        startup_password: 设置中心配置的开屏密码（仅注入 SHA-256 摘要，不注入明文）。

    Returns:
        完整的 HTML 字符串。
    """
    labels = get_labels(locale)
    lang = "zh-CN" if (locale or "zh_CN") == "zh_CN" else "en"
    replacements = {
        "__LANG__": lang,
        "__APP_RUNTIME_JS__": APP_RUNTIME_JS,
        "__DATA_SOURCE_JS__": DATA_SOURCE_JS,
        "__APP_SHELL_CSS__": APP_SHELL_CSS,
        "__APP_ROUTER_JS__": APP_ROUTER_JS,
        "__TITLE_GUARD_JS__": TITLE_GUARD_JS,
        "__LABELS_JSON__": _js_json(labels),
        "__SECRET_JSON__": _js_json(secret or ""),
        "__OFFLINE_MODE__": "true" if offline_books is not None else "false",
        "__OFFLINE_BOOKS_JSON__": _js_json(offline_books or []),
        "__BACKEND_URL_JSON__": _js_json(backend_url or ""),
        "__RESPONSIVE_CSS__": RESPONSIVE_CSS,
        "__PORTAL_CSS__": PORTAL_CSS,
        "__PORTAL_JS__": _PORTAL_JS,
        "__STARTUP_GATE_EARLY__": render_startup_gate_early_js(
            bool(startup_password_enabled), startup_password_hash(startup_password)),
        "__STARTUP_GATE_CSS__": STARTUP_GATE_CSS,
        "__STARTUP_GATE_HTML__": STARTUP_GATE_HTML,
        "__STARTUP_GATE_JS__": STARTUP_GATE_JS,
        "__SCROLL_NAV_CSS__": SCROLL_NAV_CSS,
        "__SCROLL_NAV_HTML__": SCROLL_NAV_HTML,
        "__SCROLL_NAV_JS__": SCROLL_NAV_JS,
        "__PORTAL_TITLE__": labels["portal_title"],
        "__PORTAL_TAGLINE__": labels["portal_tagline"],
        "__PORTAL_COUNT__": labels["portal_count"].replace("%d", "0"),
        "__PORTAL_SEARCH__": labels["portal_search"],
        "__PORTAL_PAGE_LABEL__": labels["portal_page_label"],
        "__PORTAL_PREV__": labels["portal_prev"],
        "__PORTAL_NEXT__": labels["portal_next"],
        "__PORTAL_REFRESH__": labels["portal_refresh"],
        "__PORTAL_UPLOAD__": labels["portal_upload"],
        "__PORTAL_EMPTY__": labels["portal_empty"],
        "__PORTAL_ONLINE_BOOKS__": labels["portal_online_books"],
        "__PORTAL_OFFLINE_BOOKS__": labels["portal_offline_books"],
        "__PORTAL_HISTORY__": labels["portal_history"],
        "__PORTAL_LOCAL_BOOKS__": labels["portal_local_books"],
        "__PORTAL_NETWORK_BOOKS__": labels["portal_network_books"],
        "__PORTAL_SETTINGS__": labels["portal_settings"],
        "__PORTAL_CLEAR_CACHE__": labels["portal_clear_cache"],
        "__PORTAL_LOADING__": labels["portal_loading"],
        "__PORTAL_MANAGE_LOCAL__": labels["portal_manage_local"],
        "__PORTAL_SELECT_ALL__": labels["portal_select_all"],
        "__PORTAL_DELETE_SELECTED__": labels["portal_delete_selected"],
        "__PORTAL_DELETE_ALL__": labels["portal_delete_all"],
        "__PORTAL_CANCEL__": labels["portal_cancel"],
        "__LIBRARY__": labels["library"],
        "__NETWORK__": labels["network"],
        "__BACKEND__": labels["backend"],
        "__API_KEY__": labels["api_key"],
        "__SAVE__": labels["save"],
        "__OFFLINE_HINT__": labels["offline_hint"],
        "__APPEARANCE__": labels["appearance"],
        "__FONT_SIZE__": labels["font_size"],
        "__LINE_HEIGHT__": labels["line_height"],
        "__NIGHT_MODE__": labels["night_mode"],
        "__ONLINE__": labels["online"],
        "__OFFLINE__": labels["offline"],
    }
    html = _PORTAL_TEMPLATE
    for token, value in replacements.items():
        html = html.replace(token, value)
    return html
