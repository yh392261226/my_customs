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

    /* --- 正文：全宽、触屏友好 --- */
    html.br-compact body, .br-web body {
        max-width: 100% !important;
        padding: 12px 14px calc(76px + var(--br-nav-safe)) 14px !important;
        font-size: 17px !important; line-height: 1.8 !important;
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
    .br-compact .toc-toggle-btn, .br-web .toc-toggle-btn {
        top: auto !important; bottom: calc(var(--br-nav-offset) + 20px) !important; right: 14px !important;
    }
    .br-compact .bookmark-btn, .br-web .bookmark-btn {
        top: auto !important; bottom: calc(var(--br-nav-offset) + 20px) !important; right: 68px !important;
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
    function cacheCurrentBook() {
        var el = $('content');
        if (!el || !el.innerHTML) { return; }
        var id = safe(function () { return window.__BR_BOOK_ID__; }) || document.title || 'book';
        openCacheDB().then(function (db) {
            var tx = db.transaction(CACHE_STORE, 'readwrite');
            tx.objectStore(CACHE_STORE).put({
                id: String(id), title: document.title,
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
                updateSetting('font_size', fs.value);
                callGlobal('changeFontSize', 0);
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
const CACHE = 'br-reader-v1';
/* 缓存键去掉 ?key=（密钥变化不应导致缓存失效），但保留 /reader 的 path（每本书独立缓存） */
function cacheKey(raw) {
    var u = new URL(raw);
    var k = u.origin + u.pathname;
    if (u.pathname === '/reader') { k += '?path=' + encodeURIComponent(u.searchParams.get('path') || ''); }
    return k;
}
/* 不做 install 预缓存：配置了接口密钥时匿名请求 '/' 会拿到 401 页面并污染缓存 */
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
    e.waitUntil(caches.keys().then(function (keys) {
        return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
    var req = e.request;
    if (req.method !== 'GET') { return; }
    var url = new URL(req.url);
    if (url.origin !== self.location.origin) { return; }
    if (url.pathname === '/sw.js' || url.pathname === '/health_check' || url.pathname === '/manifest.webmanifest') { return; }
    if (url.pathname.indexOf('/api/') === 0) { return; }

    if (req.mode === 'navigate' || url.pathname === '/' || url.pathname === '/reader') {
        var key = cacheKey(req.url);
        e.respondWith(
            fetch(req).then(function (res) {
                if (res && res.ok) {
                    var copy = res.clone();
                    caches.open(CACHE).then(function (c) { c.put(key, copy); }).catch(function () {});
                }
                return res;
            }).catch(function () {
                return caches.match(key).then(function (hit) {
                    return hit || caches.match(new URL('/', self.location.origin).href) || new Response(
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
        "offline_hint": "后端关闭后仍可继续阅读：正文已保存在本机，进度暂存本地，恢复连接后自动同步。",
        "online": "在线", "offline": "离线",
        "portal_title": "书库", "portal_search": "搜索书名 / 作者",
        "portal_tagline": "随时读，随身带", "portal_count": "共 %d 本", "portal_found": "找到 %d 本",
        "portal_page": "第 %d / %d 页", "portal_page_label": "分页",
        "portal_prev": "上一页", "portal_next": "下一页",
        "portal_refresh": "刷新", "portal_empty": "暂无书籍", "portal_no_match": "没有找到匹配的书籍",
        "portal_offline_books": "离线书籍", "portal_online_books": "书库",
        "portal_offline_tip": "后端已关闭，显示本机缓存", "portal_online_tip": "已连接后端",
        "portal_no_offline": "还没有离线缓存的书籍，请在线打开一次",
        "portal_settings": "设置", "portal_back": "返回",
        "portal_clear_cache": "清除离线缓存", "portal_cleared": "已清除",
        "portal_open_failed": "打开失败，请检查后端与密钥",
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
        "offline_hint": "You can keep reading when the backend is down: content is cached on this device and progress is stored locally until the connection returns.",
        "online": "Online", "offline": "Offline",
        "portal_title": "Library", "portal_search": "Search title / author",
        "portal_tagline": "Books, anywhere", "portal_count": "%d books", "portal_found": "%d found",
        "portal_page": "Page %d / %d", "portal_page_label": "Pagination",
        "portal_prev": "Previous page", "portal_next": "Next page",
        "portal_refresh": "Refresh", "portal_empty": "No books", "portal_no_match": "No matching books",
        "portal_offline_books": "Offline", "portal_online_books": "Library",
        "portal_offline_tip": "Backend offline, showing local cache", "portal_online_tip": "Connected to backend",
        "portal_no_offline": "No cached books yet — open one while online",
        "portal_settings": "Settings", "portal_back": "Back",
        "portal_clear_cache": "Clear offline cache", "portal_cleared": "Cleared",
        "portal_open_failed": "Failed to open, check backend and API key",
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
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; word-break:normal;
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

_PORTAL_TEMPLATE = r"""<!DOCTYPE html>
<html lang="__LANG__">
<head>
<meta charset="UTF-8">
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
</style>
</head>
<body>
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
      <button type="button" id="tabOnline" class="br-portal-tab active" role="tab">__PORTAL_ONLINE_BOOKS__</button>
      <button type="button" id="tabOffline" class="br-portal-tab" role="tab">__PORTAL_OFFLINE_BOOKS__</button>
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
  <div class="br-settings-head" style="background:var(--br-card-bg)">
    <button type="button" id="offlineBack">&#8592;</button>
    <h2 id="offlineTitle" style="font-size:16px"></h2>
  </div>
  <div class="br-offline-body" id="offlineBody"></div>
</div>

<script>
window.__BR_LABELS__ = __LABELS_JSON__;
window.__BR_BOOT_SECRET__ = __SECRET_JSON__;
</script>
<script>
__PORTAL_JS__
</script>
</body>
</html>
"""

_PORTAL_JS = r"""
(function () {
    'use strict';
    var L = window.__BR_LABELS__ || {};
    var KEY_STORE = 'br_api_secret', BACK_STORE = 'br_backend_override';
    var CACHE_KEY = 'br_portal_books', CACHE_TIME_KEY = 'br_portal_books_synced_at';
    var DB_NAME = 'br_offline_books', STORE = 'books', INDEX_STORE = 'book_index';
    var PAGE_SIZE = 20;
    var mode = 'online', books = [], offlineBooks = [], netOnline = false;
    var page = 1, total = 0, keyword = '', reqSeq = 0, searchTimer = null, syncing = false;

    function $(id) { return document.getElementById(id); }
    function safe(fn) { try { return fn(); } catch (e) { return null; } }
    function backend() {
        var o = safe(function () { return localStorage.getItem(BACK_STORE); });
        return (o || location.origin).replace(/\/+$/, '');
    }
    function key() {
        return safe(function () { return localStorage.getItem(KEY_STORE); }) || window.__BR_BOOT_SECRET__ || '';
    }
    function withKey(url) {
        var k = key();
        return k ? url + (url.indexOf('?') >= 0 ? '&' : '?') + 'key=' + encodeURIComponent(k) : url;
    }
    function headers() {
        var h = { 'Content-Type': 'application/json' };
        var k = key();
        if (k) { h['X-API-Key'] = k; }
        return h;
    }
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
        var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
        var timer = setTimeout(function () { if (ctrl) { ctrl.abort(); } }, 2500);
        return fetch(backend() + '/health_check', ctrl ? { signal: ctrl.signal, cache: 'no-store' } : { cache: 'no-store' })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) { netOnline = !!(d && d.status === 'ok'); })
            .catch(function () { netOnline = false; })
            .then(function () { clearTimeout(timer); paintNet(); return netOnline; });
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
        var hay = [b.title, b.novel_title, b.name, b.book_name, b.author, b.pinyin, b.tags, b.path]
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
            path: b.path || '', title: b.title || b.novel_title || b.name || '',
            author: b.author || '', format: b.format || '', status: b.status || '',
            pinyin: b.pinyin || '', tags: b.tags || ''
        };
    }
    function mergeCache(items) {
        if (!items || !items.length) { return; }
        safe(function () {
            var all = cachedBooks(), index = {};
            all.forEach(function (b, i) { index[String(b.path || b.title || i)] = i; });
            items.forEach(function (b) {
                var slim = slimBook(b), k = String(slim.path || slim.title);
                if (index[k] === undefined) { index[k] = all.length; all.push(slim); }
                else { all[index[k]] = slim; }
            });
            localStorage.setItem(CACHE_KEY, JSON.stringify(all));
        });
    }
    /* 后台一次拉取全量「精简书单」写入 IndexedDB：主列表仍是每页 20 条的
       服务端分页，这一步只保证后端关闭后离线书库/离线搜索覆盖全部书籍。
       走 /api/books/index（后端只 SELECT 轻量列，不含 metadata），10 分钟节流；
       localStorage 只留少量「已浏览页」兜底，避免上万本书超出配额。 */
    function syncOfflineIndex() {
        if (syncing || !netOnline) { return; }
        var last = parseInt(safe(function () { return localStorage.getItem(CACHE_TIME_KEY); }) || '0', 10) || 0;
        if (Date.now() - last < 10 * 60 * 1000) { return; }
        syncing = true;
        fetch(withKey(backend() + '/api/books/index'), { headers: headers(), cache: 'no-store' })
            .then(function (r) { return r.ok ? r.json() : null; })
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
            render(sliceLocal(list), total);
        });
    }
    function loadBooks(targetPage) {
        if (typeof targetPage === 'number') { page = Math.max(1, targetPage); }
        keyword = keywordOf();
        var seq = ++reqSeq;
        if (mode === 'offline') { loadOfflineBooks(); return Promise.resolve(); }
        return checkNet().then(function (online) {
            if (!online) {
                netOnline = false; paintNet();
                return renderOfflineFallback(seq);
            }
            var url = backend() + '/api/books?page=' + page + '&page_size=' + PAGE_SIZE +
                      (keyword ? '&q=' + encodeURIComponent(keyword) : '');
            return fetch(withKey(url), { headers: headers(), cache: 'no-store' })
                .then(function (r) { if (!r.ok) { throw new Error('http ' + r.status); } return r.json(); })
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
            /* v2 增加 book_index：全量书单放 localStorage 会超 5MB 配额，
               IndexedDB 才能容纳上万本书的离线索引。 */
            var req = indexedDB.open(DB_NAME, 2);
            req.onupgradeneeded = function () {
                var db = req.result;
                if (!db.objectStoreNames.contains(STORE)) { db.createObjectStore(STORE, { keyPath: 'id' }); }
                if (!db.objectStoreNames.contains(INDEX_STORE)) { db.createObjectStore(INDEX_STORE, { keyPath: 'id' }); }
            };
            req.onsuccess = function () { resolve(req.result); };
            req.onerror = function () { reject(req.error); };
        });
    }
    function indexRecord(b) {
        var s = slimBook(b);
        s.id = String(s.path || s.title || Math.random());
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
    function openOfflineBook(id) {
        return openDB().then(function (db) {
            return new Promise(function (resolve) {
                var tx = db.transaction(STORE, 'readonly');
                var req = tx.objectStore(STORE).get(id);
                req.onsuccess = function () { db.close(); resolve(req.result || null); };
                req.onerror = function () { db.close(); resolve(null); };
            });
        }).then(function (rec) {
            if (!rec) { return; }
            $('offlineTitle').textContent = rec.title || id;
            $('offlineBody').innerHTML = rec.html || '';
            applyReaderSettings();
            $('offlineReader').classList.add('open');
            $('portalRoot').style.display = 'none';
        }).catch(function () {});
    }

    function applyReaderSettings() {
        var s = safe(function () { return JSON.parse(localStorage.getItem('readerSettings') || '{}'); }) || {};
        var body = $('offlineBody');
        if (s.font_size) { body.style.fontSize = s.font_size + 'px'; }
        if (s.line_height) { body.style.lineHeight = s.line_height; }
        if (s.font_family) { body.style.fontFamily = s.font_family; }
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
        var title = String(b.title || b.novel_title || b.name || b.path || L.portal_title);

        var cover = document.createElement('div');
        cover.className = 'book-cover book-cover--' + coverTone(title);
        cover.setAttribute('aria-hidden', 'true');
        cover.textContent = (title.trim().charAt(0) || '书').toUpperCase();

        var meta = document.createElement('div');
        meta.className = 'book-meta';
        var h = document.createElement('h3');
        h.textContent = title;
        var author = document.createElement('p');
        author.className = 'book-author';
        author.textContent = b.author || (mode === 'offline' ? L.portal_offline_books : '—');
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
        if (mode === 'offline') {
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

        card.appendChild(cover);
        card.appendChild(meta);
        card.appendChild(arrow);
        card.addEventListener('click', function () {
            if (mode === 'offline') { openOfflineBook(b.id); return; }
            var path = b.path || '';
            if (!path) { return; }
            location.href = withKey('/reader?path=' + encodeURIComponent(path));
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
        var current = mode === 'offline' ? 'offline' : 'library';
        Array.prototype.forEach.call($('brMobileNav').querySelectorAll('button[data-nav]'), function (btn) {
            btn.classList.toggle('active', btn.getAttribute('data-nav') === current);
        });
    }

    function setMode(m) {
        mode = m;
        page = 1;
        $('tabOnline').classList.toggle('active', m === 'online');
        $('tabOffline').classList.toggle('active', m === 'offline');
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
    }

    function bind() {
        $('refreshBtn').addEventListener('click', function () { loadBooks(1); });
        $('searchInput').addEventListener('input', function () {
            if (searchTimer) { clearTimeout(searchTimer); }
            searchTimer = setTimeout(function () { loadBooks(1); }, 250);
        });
        $('prevPage').addEventListener('click', function () { goPage(page - 1); });
        $('nextPage').addEventListener('click', function () { goPage(page + 1); });
        $('tabOnline').addEventListener('click', function () { setMode('online'); });
        $('tabOffline').addEventListener('click', function () { setMode('offline'); });
        $('brMobileNav').addEventListener('click', function (e) {
            var btn = e.target.closest ? e.target.closest('button[data-nav]') : null;
            if (!btn) { return; }
            var which = btn.getAttribute('data-nav');
            Array.prototype.forEach.call($('brMobileNav').querySelectorAll('button'), function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            if (which === 'settings') { openSettings(); }
            else { closeSettings(); setMode(which === 'offline' ? 'offline' : 'online'); }
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
        $('offlineBack').addEventListener('click', function () {
            $('offlineReader').classList.remove('open');
            $('portalRoot').style.display = '';
        });
        setInterval(checkNet, 30000);
    }

    function init() {
        document.body.classList.add('br-web');
        bind();
        paintNet();
        loadBooks(1);
        loadOfflineBooks();
        if ('serviceWorker' in navigator && (location.protocol === 'http:' || location.protocol === 'https:')) {
            navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
        }
    }
    if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); } else { init(); }
})();
"""


def build_portal_html(locale: Optional[str] = None, secret: str = "") -> str:
    """生成局域网书库入口页（在线 / 离线共用同一页面）。

    Args:
        locale: 界面语言；None 时读取全局 i18n。
        secret: 后端接口密钥，仅作为首次访问的默认值写入页面（之后由 localStorage 覆盖）。

    Returns:
        完整的 HTML 字符串。
    """
    labels = get_labels(locale)
    lang = "zh-CN" if (locale or "zh_CN") == "zh_CN" else "en"
    replacements = {
        "__LANG__": lang,
        "__LABELS_JSON__": _js_json(labels),
        "__SECRET_JSON__": _js_json(secret or ""),
        "__RESPONSIVE_CSS__": RESPONSIVE_CSS,
        "__PORTAL_CSS__": PORTAL_CSS,
        "__PORTAL_JS__": _PORTAL_JS,
        "__PORTAL_TITLE__": labels["portal_title"],
        "__PORTAL_TAGLINE__": labels["portal_tagline"],
        "__PORTAL_COUNT__": labels["portal_count"].replace("%d", "0"),
        "__PORTAL_SEARCH__": labels["portal_search"],
        "__PORTAL_PAGE_LABEL__": labels["portal_page_label"],
        "__PORTAL_PREV__": labels["portal_prev"],
        "__PORTAL_NEXT__": labels["portal_next"],
        "__PORTAL_REFRESH__": labels["portal_refresh"],
        "__PORTAL_EMPTY__": labels["portal_empty"],
        "__PORTAL_ONLINE_BOOKS__": labels["portal_online_books"],
        "__PORTAL_OFFLINE_BOOKS__": labels["portal_offline_books"],
        "__PORTAL_SETTINGS__": labels["portal_settings"],
        "__PORTAL_CLEAR_CACHE__": labels["portal_clear_cache"],
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
