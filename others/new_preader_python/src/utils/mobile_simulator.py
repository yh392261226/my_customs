# -*- coding: utf-8 -*-
"""
HTML 手机模拟器（移动端网页浏览器）

背景：部分书籍站点（如 87nb）只在移动端 User-Agent / 移动端请求头下返回内容，
桌面浏览器打开时拿不到任何数据。本模块提供一个"在浏览器标签页里运行的手机"：

  1. 本地 HTTP 服务（仅监听 127.0.0.1）提供一个手机外壳 HTML 页面；
  2. 页面把目标网址交给同源代理 /proxy；
  3. 代理用完整的移动端请求头（UA / Sec-CH-UA-Mobile / Sec-Fetch-* / Referer 等）
     与 CookieJar 会话抓取目标网页，跟随重定向；
  4. 代理重写 HTML/CSS 里的链接与资源地址，使其全部回流到 /proxy，
     并在页面最前面注入桥接脚本，伪造 navigator / screen / 触摸能力、
     拦截链接点击与表单提交、处理动态插入的节点；
  5. 外壳页面负责地址栏、前进/后退/刷新、设备预设切换、自定义 UA、
     横竖屏、缩放、查看源码等。

对外入口：
    open_mobile_simulator(url="", device="", ua="") -> (bool, str)
    其中 url 会通过 ?url=<encoded> 参数传给页面，因此本功能天然支持网址参数。
"""

from __future__ import annotations

import copy
import html as html_lib
import json
import re
import secrets
import socket
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlparse

import requests

from src.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:  # pragma: no cover - 可选依赖
    pass


# --------------------------------------------------------------------------- #
# 设备预设
# --------------------------------------------------------------------------- #
DEVICE_PRESETS: Dict[str, Dict[str, Any]] = {
    "iphone": {
        "label": "iPhone 15 Pro · iOS 17 Safari",
        "width": 393,
        "height": 852,
        "dpr": 3,
        "touch": True,
        "platform": "iPhone",
        "vendor": "Apple Computer, Inc.",
        "ch_platform": '"iOS"',
        "ua": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
               "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
               "Mobile/15E148 Safari/604.1"),
    },
    "android": {
        "label": "Pixel 8 · Android 14 Chrome",
        "width": 412,
        "height": 915,
        "dpr": 2.625,
        "touch": True,
        "platform": "Linux armv8l",
        "vendor": "Google Inc.",
        "ch_platform": '"Android"',
        "ua": ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"),
    },
    "wechat": {
        "label": "微信内置浏览器 · iPhone",
        "width": 390,
        "height": 844,
        "dpr": 3,
        "touch": True,
        "platform": "iPhone",
        "vendor": "Apple Computer, Inc.",
        "ch_platform": '"iOS"',
        "ua": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
               "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
               "MicroMessenger/8.0.49(0x18003128) NetType/WIFI Language/zh_CN"),
    },
    "ipad": {
        "label": "iPad Pro · iPadOS 17 Safari",
        "width": 834,
        "height": 1194,
        "dpr": 2,
        "touch": True,
        "platform": "MacIntel",
        "vendor": "Apple Computer, Inc.",
        "ch_platform": '"iOS"',
        "ua": ("Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) "
               "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
               "Mobile/15E148 Safari/604.1"),
    },
    "desktop": {
        "label": "桌面 Chrome · 用于对比（PC 模式）",
        "width": 1280,
        "height": 800,
        "dpr": 1,
        "touch": False,
        "platform": "MacIntel",
        "vendor": "Google Inc.",
        "ch_platform": '"macOS"',
        "ua": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 (KHTML, like Gecko) "
               "Chrome/120.0.0.0 Safari/537.36"),
    },
}

DEFAULT_DEVICE = "iphone"
DEFAULT_START_URL = "https://www.baidu.com"


# --------------------------------------------------------------------------- #
# 注入到目标页面（iframe 内）的桥接脚本
# --------------------------------------------------------------------------- #
_BRIDGE_JS = r"""
(function () {
  'use strict';
  var C = __MS_BRIDGE_CONFIG__;

  function abs(u) {
    var s = String(u == null ? '' : u).trim();
    if (!s) return '';
    if (/^[a-z][a-z0-9+.-]*:/i.test(s) || s.indexOf('//') === 0) {
      try { return new URL(s, C.baseUrl).href; } catch (e) { return s; }
    }
    try { return new URL(s, C.baseUrl).href; } catch (e) { return s; }
  }

  function prox(u) {
    var s = String(u == null ? '' : u).trim();
    if (!s) return s;
    if (s.indexOf('/proxy?') === 0) return s;
    if (/^(?:#|javascript:|data:|mailto:|tel:|sms:|about:|blob:)/i.test(s)) return s;
    var a = abs(s);
    if (!/^https?:\/\//i.test(a)) return s;
    var q = '/proxy?url=' + encodeURIComponent(a) +
            '&t=' + encodeURIComponent(C.token) +
            '&d=' + encodeURIComponent(C.device);
    if (C.uaCustom) q += '&ua=' + encodeURIComponent(C.uaCustom);
    return q;
  }

  function post(msg) {
    try { parent.postMessage(msg, '*'); } catch (e) {}
  }

  /* ---------- 伪造移动端运行环境 ---------- */
  function def(obj, key, val) {
    try {
      Object.defineProperty(obj, key, {
        get: function () { return val; }, configurable: true
      });
    } catch (e) {}
  }
  try {
    def(navigator, 'userAgent', C.ua);
    def(navigator, 'appVersion', C.ua);
    def(navigator, 'platform', C.platform);
    def(navigator, 'vendor', C.vendor);
    def(navigator, 'maxTouchPoints', C.touch ? 5 : 0);
    def(window, 'devicePixelRatio', C.dpr);
    def(screen, 'width', C.width);
    def(screen, 'height', C.height);
    def(screen, 'availWidth', C.width);
    def(screen, 'availHeight', C.height);
    if (C.touch) {
      if (!('ontouchstart' in window)) { try { window.ontouchstart = null; } catch (e) {} }
      if (!window.TouchEvent) { try { window.TouchEvent = function () {}; } catch (e) {} }
      try {
        window.matchMedia = (function (orig) {
          return function (q) {
            if (q && /pointer\s*:\s*coarse|hover\s*:\s*none/i.test(q)) {
              return { matches: true, media: q, addListener: function () {},
                       removeListener: function () {}, addEventListener: function () {},
                       removeEventListener: function () {} };
            }
            return orig.call(window, q);
          };
        })(window.matchMedia || function () { return { matches: false }; });
      } catch (e) {}
    }
  } catch (e) {}

  /* ---------- URL 重写 ---------- */
  function rewriteCss(text) {
    if (!text || text.indexOf('url(') === -1 && text.indexOf('@import') === -1) return text;
    var out = String(text);
    out = out.replace(/url\(\s*(['"]?)([^'")]+)\1\s*\)/gi, function (m, q, u) {
      return 'url(' + q + prox(u) + q + ')';
    });
    out = out.replace(/(@import\s+(?:url\()?\s*['"])([^'"]+)(['"])/gi, function (m, a, u, b) {
      return a + prox(u) + b;
    });
    return out;
  }

  var ATTRS = ['src', 'href', 'action', 'poster', 'data-src', 'data-original',
               'data-url', 'data-background-image', 'background'];

  function rewriteEl(el) {
    if (!el || el.nodeType !== 1 || el.getAttribute('data-ms-done') === '1') return;
    try {
      for (var i = 0; i < ATTRS.length; i++) {
        var a = ATTRS[i];
        if (!el.hasAttribute(a)) continue;
        var v = el.getAttribute(a);
        if (!v) continue;
        var p = prox(v);
        if (p !== v) {
          if (!el.hasAttribute('data-ms-original')) {
            el.setAttribute('data-ms-original', abs(v));
          }
          el.setAttribute(a, p);
        }
      }
      if (el.hasAttribute('srcset')) {
        el.setAttribute('srcset', el.getAttribute('srcset').split(',').map(function (part) {
          var m = part.trim().match(/^(\S+)(\s+.*)?$/);
          return m ? prox(m[1]) + (m[2] || '') : part;
        }).join(', '));
      }
      var st = el.getAttribute('style');
      if (st && st.indexOf('url(') !== -1) el.setAttribute('style', rewriteCss(st));
      if (el.tagName === 'STYLE' && el.textContent.indexOf('url(') !== -1) {
        el.textContent = rewriteCss(el.textContent);
      }
      el.setAttribute('data-ms-done', '1');
    } catch (e) {}
  }

  function rewriteAll(root) {
    try {
      var nodes = (root && root.querySelectorAll)
        ? root.querySelectorAll('a,img,script,link,iframe,form,source,video,audio,embed,object,style,[style],[srcset],input,meta[http-equiv]')
        : [];
      for (var i = 0; i < nodes.length; i++) rewriteEl(nodes[i]);
      if (root && root.nodeType === 1) rewriteEl(root);
    } catch (e) {}
  }

  /* ---------- 链接点击 / 表单提交交给外壳导航 ---------- */
  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var t = e.target;
    var a = t && t.closest ? t.closest('a[href]') : null;
    if (!a) return;
    var target = (a.getAttribute('target') || '').toLowerCase();
    /* download 链接即便 target=_blank 也交给外壳导航，避免浏览器把 /proxy 直接存成文件 */
    if (target && target !== '_self' && !a.hasAttribute('download')) return;
    var raw = a.getAttribute('data-ms-original') || a.getAttribute('href') || '';
    if (raw.indexOf('/proxy?') === 0) {
      try { raw = decodeURIComponent((raw.split('url=')[1] || '').split('&')[0]); } catch (err) {}
    }
    if (!raw || /^(?:#|javascript:|mailto:|tel:|sms:|data:)/i.test(raw)) return;
    e.preventDefault();
    e.stopPropagation();
    post({ type: 'ms-navigate', url: abs(raw) });
  }, true);

  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (!f || f.tagName !== 'FORM') return;
    if (((f.getAttribute('method') || 'get') + '').toLowerCase() !== 'get') return;
    e.preventDefault();
    var action = f.getAttribute('data-ms-original') || f.getAttribute('action') || C.baseUrl;
    if (action.indexOf('/proxy?') === 0) {
      try { action = decodeURIComponent((action.split('url=')[1] || '').split('&')[0]); } catch (err) {}
    }
    var u;
    try { u = new URL(abs(action)); } catch (err) { return; }
    try {
      new FormData(f).forEach(function (v, k) { if (typeof v === 'string') u.searchParams.append(k, v); });
    } catch (err) {}
    post({ type: 'ms-navigate', url: u.href });
  }, true);

  /* ---------- 动态节点 / XHR / fetch ---------- */
  try {
    var mo = new MutationObserver(function (records) {
      for (var i = 0; i < records.length; i++) {
        var added = records[i].addedNodes || [];
        for (var j = 0; j < added.length; j++) {
          if (added[j].nodeType === 1) { rewriteEl(added[j]); rewriteAll(added[j]); }
        }
      }
    });
    mo.observe(document.documentElement || document, { childList: true, subtree: true });
  } catch (e) {}

  try {
    var _fetch = window.fetch;
    if (_fetch) {
      window.fetch = function (input, init) {
        if (typeof input === 'string') input = prox(input);
        return _fetch.call(window, input, init);
      };
    }
    var _open = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function () {
      var args = Array.prototype.slice.call(arguments);
      if (args.length > 1) args[1] = prox(args[1]);
      return _open.apply(this, args);
    };
  } catch (e) {}

  /* ---------- 通知外壳加载完成 ---------- */
  var posted = false;
  function loaded() {
    if (posted) return;
    posted = true;
    post({
      type: 'ms-loaded',
      url: C.baseUrl,
      status: C.status,
      elapsed: C.elapsed,
      contentType: C.contentType,
      title: document.title || ''
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loaded, { once: true });
  } else {
    loaded();
  }
  setTimeout(loaded, 1200);
})();
"""


# --------------------------------------------------------------------------- #
# 手机外壳页面
# --------------------------------------------------------------------------- #
_SHELL_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>📱 手机模拟器 · NewReader</title>
<style>
  :root {
    --bg: #0d1117; --panel: #161b22; --line: #2b3441; --text: #e6edf3;
    --muted: #8b949e; --accent: #58a6ff; --accent2: #3fb950; --danger: #f85149;
    --phone-w: 393px; --phone-h: 852px; --scale: 1;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body {
    background: radial-gradient(1200px 700px at 15% -10%, #1b2738 0%, transparent 60%),
                radial-gradient(900px 600px at 100% 100%, #1a2233 0%, transparent 55%),
                var(--bg);
    color: var(--text);
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
          "Microsoft YaHei", sans-serif;
    display: flex; flex-direction: column; overflow: hidden;
  }
  .topbar {
    display: flex; align-items: center; gap: 14px; padding: 12px 22px;
    border-bottom: 1px solid var(--line); background: rgba(22,27,34,.72);
    backdrop-filter: blur(12px); flex: none;
  }
  .topbar h1 { font-size: 16px; margin: 0; font-weight: 650; letter-spacing: .3px; }
  .topbar .sub { color: var(--muted); font-size: 12px; }
  .topbar .spacer { flex: 1; }
  .badge {
    font-size: 11px; color: var(--accent2); border: 1px solid #23532f;
    background: #10251a; padding: 3px 9px; border-radius: 999px; white-space: nowrap;
  }
  .workspace {
    flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center;
    gap: 34px; padding: 20px; overflow: auto;
  }
  .stage {
    flex: none; display: flex; align-items: center; justify-content: center;
    width: calc(var(--phone-w) * var(--scale) + 40px);
    height: calc(var(--phone-h) * var(--scale) + 40px);
  }
  .phone {
    width: var(--phone-w); height: var(--phone-h);
    transform: scale(var(--scale)); transform-origin: center center;
    background: #05070a; border: 11px solid #171a1f; border-radius: 52px;
    box-shadow: 0 0 0 2px #343b47, 0 26px 70px rgba(0,0,0,.65),
                inset 0 0 0 1px rgba(255,255,255,.05);
    display: flex; flex-direction: column; overflow: hidden; position: relative;
    transition: width .18s ease, height .18s ease, transform .18s ease;
  }
  .notch {
    position: absolute; top: 0; left: 50%; transform: translateX(-50%);
    width: 118px; height: 27px; background: #05070a;
    border-bottom-left-radius: 18px; border-bottom-right-radius: 18px; z-index: 6;
  }
  .statusbar {
    height: 42px; flex: none; padding: 0 24px; display: flex; align-items: center;
    justify-content: space-between; font-size: 12px; font-weight: 600;
    color: #f2f4f8; background: var(--sb-bg, #fff); position: relative; z-index: 5;
  }
  .statusbar .icons { display: flex; gap: 7px; align-items: center; font-size: 12px; }
  .urlbar {
    flex: none; display: flex; gap: 6px; align-items: center; padding: 8px 10px;
    background: var(--bar-bg, #f1f2f5); border-bottom: 1px solid rgba(0,0,0,.07);
  }
  .urlbar input {
    flex: 1; min-width: 0; border: 1px solid rgba(0,0,0,.09); border-radius: 9px;
    padding: 7px 10px; font-size: 12px; outline: none; background: #fff; color: #1b1f24;
  }
  .urlbar input:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(88,166,255,.2); }
  .urlbar button {
    border: 0; background: transparent; cursor: pointer; font-size: 15px;
    padding: 5px 7px; border-radius: 8px; color: #3c4450; line-height: 1;
  }
  .urlbar button:hover { background: rgba(0,0,0,.07); }
  #screen { flex: 1; width: 100%; border: 0; background: #fff; display: block; }
  .homebar {
    height: 22px; flex: none; background: var(--bar-bg, #f1f2f5);
    display: flex; align-items: center; justify-content: center;
  }
  .homebar i { width: 118px; height: 4px; border-radius: 4px; background: #1c2026; opacity: .75; }

  .side {
    width: 320px; flex: none; max-height: 100%; overflow: auto;
    background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
    padding: 18px; box-shadow: 0 16px 40px rgba(0,0,0,.3);
  }
  .side h2 {
    font-size: 13px; margin: 0 0 14px; color: var(--muted); font-weight: 600;
    letter-spacing: .6px; text-transform: uppercase;
  }
  .group { margin-bottom: 16px; }
  .group > label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }
  .group input[type=text], .group select, .group textarea {
    width: 100%; background: #0d1117; color: var(--text); border: 1px solid var(--line);
    border-radius: 9px; padding: 8px 10px; font-size: 12px; outline: none;
    font-family: inherit;
  }
  .group input:focus, .group select:focus, .group textarea:focus { border-color: var(--accent); }
  .group textarea { resize: vertical; min-height: 62px; line-height: 1.45; }
  .row { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn {
    background: #21262d; color: var(--text); border: 1px solid var(--line);
    border-radius: 9px; padding: 7px 11px; font-size: 12px; cursor: pointer;
    font-family: inherit; white-space: nowrap;
  }
  .btn:hover { background: #2d333b; border-color: #3d4756; }
  .btn.primary { background: #1a6ac7; border-color: #2a7ad6; color: #fff; }
  .btn.primary:hover { background: #2079dd; }
  .btn:disabled { opacity: .4; cursor: not-allowed; }
  .btn.wide { flex: 1; }
  .hint { font-size: 11px; color: var(--muted); line-height: 1.55; margin-top: 6px; }
  .chk { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text); }
  .chk input { accent-color: var(--accent); }
  .divider { height: 1px; background: var(--line); margin: 16px 0; }
  .kv { font-size: 11px; color: var(--muted); word-break: break-all; line-height: 1.6; }
  .kv b { color: #b9c3cf; font-weight: 600; }

  .footer {
    flex: none; padding: 9px 22px; border-top: 1px solid var(--line);
    background: rgba(22,27,34,.8); display: flex; gap: 12px; align-items: center;
    font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden;
  }
  .footer .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent2); flex: none; }
  .footer .dot.busy { background: #d29922; }
  .footer .dot.err { background: var(--danger); }
  .footer #status-text { overflow: hidden; text-overflow: ellipsis; }

  .modal {
    position: fixed; inset: 0; background: rgba(0,0,0,.72); z-index: 50;
    display: none; align-items: center; justify-content: center; padding: 40px;
  }
  .modal.show { display: flex; }
  .modal-box {
    width: min(1000px, 100%); height: 100%; background: var(--panel);
    border: 1px solid var(--line); border-radius: 14px; display: flex;
    flex-direction: column; overflow: hidden;
  }
  .modal-head {
    padding: 12px 16px; border-bottom: 1px solid var(--line);
    display: flex; align-items: center; gap: 10px; font-size: 13px;
  }
  .modal-head .spacer { flex: 1; }
  .modal-body { flex: 1; overflow: auto; padding: 14px 16px; }
  .modal-body pre {
    margin: 0; font: 12px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    white-space: pre-wrap; word-break: break-all; color: #c9d5e3;
  }
  @media (max-width: 980px) {
    .workspace { flex-direction: column; gap: 18px; justify-content: flex-start; }
    .side { width: min(100%, 560px); }
  }
</style>
</head>
<body>

<div class="topbar">
  <h1>📱 手机模拟器</h1>
  <span class="sub">移动端 UA 代理浏览 · 用于排查仅手机可访问的站点</span>
  <span class="spacer"></span>
  <span class="badge" id="mode-badge">MOBILE · iPhone</span>
  <button class="btn" id="open-external" title="用系统浏览器打开原网址">↗ 原网址</button>
</div>

<div class="workspace">
  <div class="stage">
    <div class="phone" id="phone">
      <div class="notch"></div>
      <div class="statusbar">
        <span id="clock">9:41</span>
        <span class="icons"><span>▮▮▮</span><span>⌁</span><span>▰</span></span>
      </div>
      <div class="urlbar">
        <input id="addr" type="text" spellcheck="false" placeholder="输入网址后回车">
        <button id="go" title="前往">➤</button>
        <button id="reload" title="刷新">⟳</button>
      </div>
      <iframe id="screen" src="about:blank" referrerpolicy="no-referrer"></iframe>
      <div class="homebar"><i></i></div>
    </div>
  </div>

  <div class="side">
    <h2>设备与网络</h2>
    <div class="group">
      <label>设备预设（切换后自动重新加载）</label>
      <select id="device"></select>
      <div class="hint">不同站点可能只认特定 UA。若 iPhone 拿不到内容，可试 Android / 微信。</div>
    </div>
    <div class="group">
      <label>自定义 User-Agent（留空 = 使用预设 UA）</label>
      <textarea id="custom-ua" spellcheck="false" placeholder="Mozilla/5.0 (iPhone; ...)"></textarea>
      <div class="row" style="margin-top:8px">
        <button class="btn wide" id="apply-ua">应用 UA 并重载</button>
        <button class="btn" id="clear-ua">清除</button>
      </div>
    </div>
    <div class="group">
      <label>当前生效 UA</label>
      <div class="kv" id="ua-view">—</div>
    </div>
    <div class="divider"></div>

    <h2>导航</h2>
    <div class="row">
      <button class="btn" id="back">← 后退</button>
      <button class="btn" id="forward">前进 →</button>
      <button class="btn" id="refresh">⟳ 刷新</button>
      <button class="btn" id="home">⌂ 起始页</button>
    </div>
    <div class="divider"></div>

    <h2>外观与工具</h2>
    <div class="row">
      <button class="btn" id="rotate">⟲ 横竖屏</button>
      <button class="btn" id="zoom-out">－ 缩小</button>
      <button class="btn" id="zoom-in">＋ 放大</button>
      <button class="btn" id="zoom-reset">100%</button>
    </div>
    <div class="row" style="margin-top:8px">
      <button class="btn wide" id="show-source">&lt;/&gt; 查看网页源码</button>
      <button class="btn" id="copy-url">复制网址</button>
    </div>
    <div class="group" style="margin-top:14px">
      <label class="chk"><input type="checkbox" id="pc-view"> 桌面视图（仅放大外壳，UA 不变）</label>
    </div>
    <div class="divider"></div>

    <h2>本次响应</h2>
    <div class="kv" id="response-info">尚未加载页面</div>
    <div class="hint" style="margin-top:12px">
      页面、图片、脚本、样式与表单全部经本地代理转发，服务端以手机请求头抓取并维持 Cookie
      会话；页面内 <code>navigator</code> / <code>screen</code> / 触摸能力也已按设备伪造。
    </div>
  </div>
</div>

<div class="footer">
  <span class="dot" id="status-dot"></span>
  <span id="status-text">就绪</span>
</div>

<div class="modal" id="source-modal">
  <div class="modal-box">
    <div class="modal-head">
      <b>网页源码（代理抓取到的原始 HTML，未重写）</b>
      <span class="kv" id="source-meta"></span>
      <span class="spacer"></span>
      <button class="btn" id="copy-source">复制源码</button>
      <button class="btn" id="close-source">关闭</button>
    </div>
    <div class="modal-body"><pre id="source-pre"></pre></div>
  </div>
</div>

<script>
(function () {
  'use strict';
  var C = __MS_SHELL_CONFIG__;

  var TOKEN = C.token;
  var devices = C.devices;
  var device = C.defaultDevice;
  var customUA = C.defaultUA || '';
  var startUrl = C.defaultUrl;
  var history = [];
  var idx = -1;
  var scale = C.scale || 1;
  var rotated = false;

  var $ = function (id) { return document.getElementById(id); };
  var addr = $('addr'), screen = $('screen'), dot = $('status-dot'), statusText = $('status-text');

  function qs(name) {
    try { return new URLSearchParams(location.search).get(name) || ''; } catch (e) { return ''; }
  }
  function setStatus(text, kind) {
    statusText.textContent = text;
    dot.className = 'dot' + (kind ? ' ' + kind : '');
  }
  function normalize(u) {
    u = String(u || '').trim();
    if (!u) return startUrl;
    if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(u)) u = 'https://' + u;
    return u;
  }
  function proxyUrl(u) {
    var q = '/proxy?url=' + encodeURIComponent(u) + '&t=' + encodeURIComponent(TOKEN) +
            '&d=' + encodeURIComponent(device);
    if (customUA) q += '&ua=' + encodeURIComponent(customUA);
    return q;
  }
  function updateButtons() {
    $('back').disabled = idx <= 0;
    $('forward').disabled = idx >= history.length - 1;
  }
  function updateUaView() {
    $('ua-view').textContent = customUA || devices[device].ua;
    var mobile = device !== 'desktop' && !/Windows NT|Macintosh; Intel Mac OS X.*Chrome/i.test(customUA || '');
    $('mode-badge').textContent = (device === 'desktop' ? 'DESKTOP' : 'MOBILE') + ' · ' +
      (device === 'desktop' ? 'Chrome' : device.toUpperCase());
    document.querySelector('.phone').style.setProperty('--sb-bg', mobile ? '#fff' : '#eef1f5');
  }

  function navigate(u, push) {
    u = normalize(u);
    if (!/^https?:\/\//i.test(u)) { setStatus('仅支持 http / https 网址', 'err'); return; }
    if (push !== false) {
      history = history.slice(0, idx + 1);
      history.push(u);
      idx = history.length - 1;
    }
    addr.value = u;
    updateButtons();
    setStatus('正在以 ' + (device === 'desktop' ? '桌面' : '手机') + ' 身份加载：' + u, 'busy');
    $('response-info').innerHTML = '正在请求…';
    screen.src = proxyUrl(u);
  }
  function reload() { if (idx >= 0) screen.src = proxyUrl(history[idx]); }

  /* ---------- 事件绑定 ---------- */
  addr.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); navigate(addr.value); }
  });
  $('go').addEventListener('click', function () { navigate(addr.value); });
  $('reload').addEventListener('click', reload);
  $('refresh').addEventListener('click', reload);
  $('back').addEventListener('click', function () { if (idx > 0) { idx--; addr.value = history[idx]; navigate(history[idx], false); } });
  $('forward').addEventListener('click', function () { if (idx < history.length - 1) { idx++; addr.value = history[idx]; navigate(history[idx], false); } });
  $('home').addEventListener('click', function () { navigate(startUrl); });

  var sel = $('device');
  Object.keys(devices).forEach(function (k) {
    var o = document.createElement('option');
    o.value = k; o.textContent = devices[k].label;
    sel.appendChild(o);
  });
  sel.value = device;
  sel.addEventListener('change', function () {
    device = sel.value;
    applySize(); updateUaView(); reload();
  });

  $('custom-ua').value = customUA;
  $('apply-ua').addEventListener('click', function () {
    customUA = $('custom-ua').value.trim();
    updateUaView(); reload();
  });
  $('clear-ua').addEventListener('click', function () {
    customUA = ''; $('custom-ua').value = '';
    updateUaView(); reload();
  });

  function applySize() {
    var d = devices[device];
    var w = d.width, h = d.height;
    if (rotated) { var t = w; w = h; h = t; }
    if ($('pc-view').checked && device !== 'desktop') { w = Math.max(w, 900); }
    var maxH = Math.max(360, window.innerHeight - 190);
    var s = Math.min(scale, maxH / h);
    document.documentElement.style.setProperty('--phone-w', w + 'px');
    document.documentElement.style.setProperty('--phone-h', h + 'px');
    document.documentElement.style.setProperty('--scale', s.toFixed(3));
  }
  function setScale(v) { scale = Math.max(.4, Math.min(1.6, v)); applySize(); }
  $('rotate').addEventListener('click', function () { rotated = !rotated; applySize(); });
  $('zoom-out').addEventListener('click', function () { setScale(scale - .1); });
  $('zoom-in').addEventListener('click', function () { setScale(scale + .1); });
  $('zoom-reset').addEventListener('click', function () { setScale(1); });
  $('pc-view').addEventListener('change', applySize);
  window.addEventListener('resize', applySize);

  $('copy-url').addEventListener('click', function () {
    var u = addr.value || (history[idx] || startUrl);
    navigator.clipboard.writeText(u).then(function () { setStatus('已复制网址：' + u); },
      function () { setStatus('复制失败，请手动从地址栏复制', 'err'); });
  });
  $('open-external').addEventListener('click', function () {
    window.open(addr.value || (history[idx] || startUrl), '_blank', 'noopener');
  });

  $('show-source').addEventListener('click', function () {
    var u = history[idx] || startUrl;
    setStatus('正在读取源码…', 'busy');
    fetch('/raw?url=' + encodeURIComponent(u) + '&t=' + encodeURIComponent(TOKEN) +
          '&d=' + encodeURIComponent(device) + (customUA ? '&ua=' + encodeURIComponent(customUA) : ''))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var hs = Object.keys(d.headers || {}).map(function (k) { return k + ': ' + d.headers[k]; }).join('\n');
        $('source-pre').textContent = (hs ? hs + '\n\n' : '') + (d.html || d.error || '(无内容)');
        $('source-meta').textContent = d.status ? ('HTTP ' + d.status + ' · ' + d.final_url + ' · ' + d.elapsed + 'ms') : '';
        $('source-modal').classList.add('show');
        setStatus('源码与响应头已加载');
      })
      .catch(function (e) { setStatus('读取源码失败：' + e, 'err'); });
  });
  $('copy-source').addEventListener('click', function () {
    navigator.clipboard.writeText($('source-pre').textContent)
      .then(function () { setStatus('源码已复制到剪贴板'); });
  });
  $('close-source').addEventListener('click', function () { $('source-modal').classList.remove('show'); });
  $('source-modal').addEventListener('click', function (e) {
    if (e.target === this) this.classList.remove('show');
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') $('source-modal').classList.remove('show');
  });

  window.addEventListener('message', function (e) {
    var d = e.data;
    if (!d || typeof d !== 'object') return;
    if (d.type === 'ms-navigate') {
      navigate(d.url);
    } else if (d.type === 'ms-loaded') {
      if (!d.status) {
        setStatus('加载失败 · 请查看手机屏幕上的错误提示', 'err');
        $('response-info').innerHTML = '<b>状态：</b>抓取失败<br>' +
          '<b>建议：</b>切换设备预设或自定义 UA 后刷新';
        return;
      }
      setStatus('已加载 · HTTP ' + d.status + ' · ' + d.elapsed + 'ms · ' + d.url, '');
      $('response-info').innerHTML =
        '<b>状态：</b>HTTP ' + d.status + '<br>' +
        '<b>最终网址：</b>' + (d.url || '—') + '<br>' +
        '<b>类型：</b>' + (d.contentType || '—') + '<br>' +
        '<b>耗时：</b>' + d.elapsed + ' ms<br>' +
        '<b>标题：</b>' + (d.title || '—');
    }
  });

  function tick() {
    var d = new Date();
    $('clock').textContent = d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
  }
  tick(); setInterval(tick, 30000);

  /* ---------- 启动 ---------- */
  var initialURL = qs('url');
  var initialDevice = qs('device');
  var initialUA = qs('ua');
  if (initialDevice && devices[initialDevice]) { device = initialDevice; sel.value = device; }
  if (initialUA) { customUA = initialUA; $('custom-ua').value = initialUA; }
  updateUaView();
  applySize();
  navigate(initialURL || startUrl);
})();
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #
_ATTR_RE = re.compile(
    r'(?is)\b(src|href|action|poster|data-src|data-original|data-url|background)\s*=\s*'
    r'(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))'
)
_SRCSET_RE = re.compile(r'(?is)\b(srcset)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')
_CSS_URL_RE = re.compile(r'(?i)url\(\s*([\'"]?)([^\'")]+)\1\s*\)')
_CSS_IMPORT_RE = re.compile(r'(?i)(@import\s+(?:url\()?\s*[\'"])([^\'"]+)([\'"])')
_BASE_RE = re.compile(r'(?is)<base\b[^>]*>')
_CHARSET_META_RE = re.compile(r'(?is)<meta[^>]+charset\s*=\s*[^>]*>')
_CSP_META_RE = re.compile(r'(?is)<meta[^>]+http-equiv\s*=\s*["\']?content-security-policy["\']?[^>]*>')
_REFRESH_META_RE = re.compile(
    r'(?is)(<meta[^>]+http-equiv\s*=\s*["\']?refresh["\']?[^>]+content\s*=\s*["\'])([^"\']*)(["\'])'
)
_SKIP_SCHEME_RE = re.compile(r'^(?:#|javascript:|data:|mailto:|tel:|sms:|about:|blob:)', re.I)


def _safe_url(base: str, value: str) -> str:
    """把页面里的 URL 转成绝对地址；非 http(s) 的特殊协议返回空串。"""
    value = (value or "").strip()
    if not value or _SKIP_SCHEME_RE.match(value) or value.startswith("/proxy?"):
        return ""
    try:
        absolute = urljoin(base, value)
    except Exception:
        return ""
    p = urlparse(absolute)
    if p.scheme not in ("http", "https") or not p.netloc:
        return ""
    return absolute


def _decode_body(resp: requests.Response) -> str:
    """按 Content-Type / meta charset / 探测结果解码 HTML。"""
    raw = resp.content or b""
    enc = None
    m = re.search(r"charset\s*=\s*([\w\-]+)", resp.headers.get("Content-Type", ""), re.I)
    if m:
        enc = m.group(1)
    if not enc:
        head = raw[:4096].decode("ascii", errors="ignore")
        m = re.search(r"<meta[^>]+charset\s*=\s*[\"']?\s*([\w\-]+)", head, re.I)
        if m:
            enc = m.group(1)
    if not enc:
        enc = resp.apparent_encoding or resp.encoding or "utf-8"
    try:
        return raw.decode(enc, errors="replace")
    except (LookupError, TypeError):
        return raw.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- #
# 下载类响应的识别与处理
#
# 部分书籍站点（WAP 站、反爬跳转、TXT/APK 下载页）会返回 application/octet-stream、
# text/vnd.wap.wml，甚至不带 Content-Type。代理若把这类响应原样交给 iframe 导航，
# 浏览器只能按 URL 路径把内容保存成名为 "proxy" 的文件 —— 这就是浏览时
# "突然下载一个 proxy 文件" 的原因；源站 Content-Disposition 未转发也导致
# 浏览器拿不到真实文件名。
# --------------------------------------------------------------------------- #
_DOWNLOAD_MIMES = frozenset({
    "application/octet-stream", "application/octetstream", "binary/octet-stream",
    "application/x-download", "application/force-download", "application/download",
    "application/x-msdownload", "application/x-msdos-program",
    "application/zip", "application/x-zip-compressed", "application/x-rar-compressed",
    "application/x-7z-compressed", "application/gzip", "application/x-gzip",
    "application/x-tar", "application/x-bzip2",
    "application/vnd.android.package-archive", "application/epub+zip",
    "application/pdf", "application/msword", "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint", "application/x-apple-diskimage",
    "application/x-shockwave-flash", "application/x-executable",
})

_HTML_START_RE = re.compile(
    rb"(?i)<(?:!doctype\s+html|html[\s/>]|head[\s/>]|body[\s/>]|meta[\s/>]|"
    rb"title[\s/>]|wml[\s/>]|card[\s/>]|div[\s/>]|table[\s/>]|"
    rb"script[\s/>]|link[\s/>]|style[\s/>]|center[\s/>]|font[\s/>]|p[\s/>])"
)


def _looks_like_html(data: bytes) -> bool:
    """内容嗅探：不少小说站返回的 Content-Type 不可靠，但内容其实是 HTML/WML。"""
    if not data or b"\x00" in data[:512]:
        return False
    head = re.sub(rb"(?is)^(?:<\?xml[^>]*\?>|<!--.*?-->|\s)+", b"", data[:4096])
    return bool(_HTML_START_RE.match(head))


def _is_download_mime(mime: str) -> bool:
    mime = (mime or "").strip().lower()
    return (not mime or mime in _DOWNLOAD_MIMES
            or mime.startswith(("application/vnd.", "application/x-")))


def _suggested_filename(url: str, disposition: str) -> str:
    """从 Content-Disposition / URL 推断真实文件名，避免浏览器按 /proxy 命名。"""
    name = ""
    m = re.search(r"(?i)filename\*\s*=\s*UTF-8''([^;]+)", disposition or "")
    if m:
        name = unquote(m.group(1).strip().strip('"'))
    if not name:
        m = re.search(r"(?i)filename\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^;]+))", disposition or "")
        if m:
            name = (m.group(1) or m.group(2) or m.group(3) or "").strip()
    if not name:
        name = (urlparse(url).path or "").rstrip("/").split("/")[-1]
    return re.sub(r"[\r\n\"']", "", name).strip() or "download"


def _download_notice_html(final_url: str, filename: str, ctype: str,
                          size: int, elapsed: int, download_url: str) -> bytes:
    """文档导航撞上下载类响应时返回页内提示，而不是让浏览器静默下载。"""
    def esc(value: Any) -> str:
        return html_lib.escape(str(value), quote=True)

    cfg = json.dumps({"url": final_url, "status": 200, "elapsed": elapsed,
                      "contentType": ctype, "title": "下载资源（未预览）"},
                     ensure_ascii=False).replace("<", "\\u003c")
    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{{font:14px/1.7 -apple-system,'PingFang SC',sans-serif;background:#fff;
color:#24292f;padding:22px;margin:0}}h3{{margin:0 0 10px;font-size:16px}}
.k{{background:#f6f8fa;border-radius:8px;padding:12px 14px;font-size:12px;
word-break:break-all;margin:12px 0}}a{{display:inline-block;margin:4px 8px 4px 0;
padding:7px 12px;border-radius:8px;background:#1a6ac7;color:#fff;text-decoration:none;
font-size:12px}}a.sec{{background:#eef1f5;color:#24292f}}p{{color:#57606a;margin:8px 0}}</style>
</head><body>
<h3>该链接不是网页，已阻止自动下载</h3>
<p>目标站点返回的是下载类内容。手机模拟器不会把它保存到「下载」目录，也不再生成名为 <code>proxy</code> 的文件。</p>
<div class="k"><b>最终网址：</b>{esc(final_url)}<br>
<b>类型：</b>{esc(ctype)}<br><b>大小：</b>{size} 字节 · <b>耗时：</b>{elapsed} ms<br>
<b>源站文件名：</b>{esc(filename)}</div>
<a href="{esc(download_url)}" target="_blank" rel="noopener">仍然下载（保留原文件名）</a>
<a class="sec" href="{esc(final_url)}" target="_blank" rel="noopener">在系统浏览器打开原网址</a>
<p>若这是站点自动跳转（反爬 / 广告脚本 / 移动端兼容跳转），可切换设备预设或自定义 UA 后刷新。</p>
<script>parent.postMessage(Object.assign({{type:'ms-loaded'}},{cfg}),'*');</script>
</body></html>"""
    return page.encode("utf-8")


# --------------------------------------------------------------------------- #
# 主体
# --------------------------------------------------------------------------- #
class MobileSimulator:
    """本地手机模拟器服务（单例，懒启动）。"""

    _instance: Optional["MobileSimulator"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self.host = "127.0.0.1"
        self.port: Optional[int] = None
        self._server = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.token = secrets.token_urlsafe(24)
        self._jar = requests.cookies.RequestsCookieJar()
        self._jar_lock = threading.RLock()
        self._last_doc_url = ""
        self._raw_cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._raw_lock = threading.Lock()

        cfg = self._read_config()
        self.host = str(cfg.get("host") or "127.0.0.1")
        self._preferred_port = int(cfg.get("port") or 54323)
        self.start_url = str(cfg.get("start_url") or DEFAULT_START_URL)
        self.default_device = str(cfg.get("device") or DEFAULT_DEVICE)
        if self.default_device not in DEVICE_PRESETS:
            self.default_device = DEFAULT_DEVICE
        self.verify_ssl = bool(cfg.get("verify_ssl", False))
        self.timeout = (8, 25)

    # ------------------------------------------------------------------ #
    # 单例 / 配置
    # ------------------------------------------------------------------ #
    @classmethod
    def get_instance(cls) -> "MobileSimulator":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @staticmethod
    def _read_config() -> Dict[str, Any]:
        try:
            from src.config.config_manager import ConfigManager
            cfg = ConfigManager.get_instance().get_config()
            return dict(cfg.get("mobile_simulator", {}) or {})
        except Exception as e:
            logger.debug(f"读取手机模拟器配置失败，使用默认值: {e}")
            return {}

    # ------------------------------------------------------------------ #
    # 服务生命周期
    # ------------------------------------------------------------------ #
    def _port_free(self, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                return s.connect_ex((self.host, port)) != 0
        except Exception:
            return False

    def start(self) -> bool:
        with self._lock:
            if self._server is not None:
                return True
            from http.server import ThreadingHTTPServer

            port = 0
            for candidate in range(self._preferred_port, self._preferred_port + 12):
                if self._port_free(candidate):
                    port = candidate
                    break
            try:
                handler = self._build_handler()
                server = ThreadingHTTPServer((self.host, port), handler)
            except OSError as e:
                logger.error(f"手机模拟器服务启动失败: {e}")
                return False
            self.port = server.server_address[1]
            self._server = server
            self._thread = threading.Thread(
                target=server.serve_forever, name="mobile-simulator", daemon=True
            )
            self._thread.start()
            logger.info(f"手机模拟器服务已启动: http://{self.host}:{self.port}/ (token 已内置于页面)")
            return True

    def stop(self) -> None:
        with self._lock:
            if self._server:
                try:
                    self._server.shutdown()
                    self._server.server_close()
                except Exception:
                    pass
            self._server = None
            self._thread = None
            self.port = None

    def build_page_url(self, url: str = "", device: str = "", ua: str = "") -> str:
        """构造带 ?url= 参数的模拟器地址（网址参数支持）。"""
        if not self.start():
            raise RuntimeError("手机模拟器服务未能启动")
        params: Dict[str, str] = {}
        # 未显式给网址时，把配置里的起始网址也写成 ?url= 参数，
        # 保证所有入口（按钮 / 快捷键 / 手工地址）走同一条参数化路径。
        params["url"] = url or self.start_url
        if device and device in DEVICE_PRESETS:
            params["device"] = device
        if ua:
            params["ua"] = ua
        base = f"http://{self.host}:{self.port}/"
        return base + ("?" + urlencode(params) if params else "")

    def open(self, url: str = "", device: str = "", ua: str = "") -> Tuple[bool, str]:
        """启动服务并在浏览器打开手机模拟器；返回 (成功, 消息/地址)。"""
        try:
            page_url = self.build_page_url(url, device, ua)
            try:
                from src.utils.browser_manager import BrowserManager
                if BrowserManager.open_url(page_url):
                    return True, page_url
            except Exception as e:
                logger.warning(f"BrowserManager 打开手机模拟器失败，回退默认浏览器: {e}")
            import webbrowser
            webbrowser.open(page_url)
            return True, page_url
        except Exception as e:
            logger.error(f"打开手机模拟器失败: {e}", exc_info=True)
            return False, str(e)

    # ------------------------------------------------------------------ #
    # 目标站点抓取
    # ------------------------------------------------------------------ #
    def _new_session(self) -> requests.Session:
        s = requests.Session()
        with self._jar_lock:
            for cookie in self._jar:
                try:
                    s.cookies.set_cookie(copy.copy(cookie))
                except Exception:
                    pass
        s.headers.clear()  # 由本模块完全控制请求头，避免默认 python-requests UA 混入
        return s

    def _store_cookies(self, resp: requests.Response) -> None:
        try:
            with self._jar_lock:
                for cookie in resp.cookies:
                    self._jar.set_cookie(copy.copy(cookie))
        except Exception as e:
            logger.debug(f"同步手机模拟器 Cookie 失败: {e}")

    def _headers(self, device_key: str, custom_ua: str,
                 is_document: bool, content_type: str = "") -> Dict[str, str]:
        device = DEVICE_PRESETS.get(device_key) or DEVICE_PRESETS[DEFAULT_DEVICE]
        ua = custom_ua or device["ua"]
        mobile = device_key != "desktop"
        headers = {
            "User-Agent": ua,
            "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                       "image/avif,image/webp,*/*;q=0.8") if is_document
                      else "image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Sec-CH-UA-Mobile": "?1" if mobile else "?0",
            "Sec-CH-UA-Platform": device["ch_platform"],
            "Sec-Fetch-Dest": "document" if is_document else "empty",
            "Sec-Fetch-Mode": "navigate" if is_document else "no-cors",
            "Sec-Fetch-Site": "same-origin" if self._last_doc_url else "none",
        }
        if is_document:
            headers["Upgrade-Insecure-Requests"] = "1"
            headers["Sec-Fetch-User"] = "?1"
        if self._last_doc_url:
            headers["Referer"] = self._last_doc_url
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def fetch(self, url: str, device_key: str = DEFAULT_DEVICE, custom_ua: str = "",
              method: str = "GET", body: bytes = b"", content_type: str = "") -> Optional[requests.Response]:
        """以移动端身份抓取目标 URL，维持 Cookie 会话。"""
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            raise ValueError("仅支持 http / https 网址")
        if p.hostname in ("127.0.0.1", "localhost", "::1") and p.port == self.port:
            raise ValueError("目标地址不能指向手机模拟器自身")

        resource_exts = (
            ".js", ".mjs", ".css", ".png", ".jpg", ".jpeg", ".gif", ".webp",
            ".avif", ".svg", ".ico", ".bmp", ".woff", ".woff2", ".ttf", ".eot",
            ".otf", ".mp4", ".mp3", ".m3u8", ".ts", ".json", ".xml", ".pdf",
            ".zip", ".apk", ".bin",
        )
        # 表单 POST 同样是"导航"，需要带上 document/navigate 系列请求头
        is_document = not p.path.lower().endswith(resource_exts)
        session = self._new_session()
        started = time.time()
        try:
            resp = session.request(
                method, url,
                headers=self._headers(device_key, custom_ua, is_document, content_type),
                data=body if method == "POST" else None,
                allow_redirects=True,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            self._store_cookies(resp)
            if is_document and resp.url:
                with self._jar_lock:
                    self._last_doc_url = resp.url
            logger.debug(f"[手机模拟器] {method} {url} -> HTTP {resp.status_code} "
                         f"({int((time.time() - started) * 1000)}ms, {resp.url})")
            return resp
        finally:
            try:
                session.close()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # 内容重写
    # ------------------------------------------------------------------ #
    def _proxy_url(self, absolute: str, token: str, device: str, custom_ua: str) -> str:
        q = "/proxy?url=" + quote(absolute, safe="") + "&t=" + quote(token, safe="") + "&d=" + quote(device, safe="")
        if custom_ua:
            q += "&ua=" + quote(custom_ua, safe="")
        return q

    def _rewrite_css(self, text: str, base: str, token: str,
                     device: str, custom_ua: str) -> str:
        def _url_sub(m: "re.Match") -> str:
            quote_char, raw = m.group(1), m.group(2)
            absolute = _safe_url(base, raw)
            if not absolute:
                return m.group(0)
            return "url(" + quote_char + self._proxy_url(absolute, token, device, custom_ua) + quote_char + ")"

        def _import_sub(m: "re.Match") -> str:
            absolute = _safe_url(base, m.group(2))
            if not absolute:
                return m.group(0)
            return m.group(1) + self._proxy_url(absolute, token, device, custom_ua) + m.group(3)

        text = _CSS_URL_RE.sub(_url_sub, text)
        return _CSS_IMPORT_RE.sub(_import_sub, text)

    def _rewrite_html(self, body: str, final_url: str, device_key: str,
                      custom_ua: str, token: str, meta: Dict[str, Any]) -> str:
        device = DEVICE_PRESETS.get(device_key) or DEVICE_PRESETS[DEFAULT_DEVICE]
        ua = custom_ua or device["ua"]

        # 移除会干扰代理页面的标签：base / CSP / 原 charset
        body = _BASE_RE.sub("", body)
        body = _CSP_META_RE.sub("", body)
        body = _CHARSET_META_RE.sub("", body)

        def _attr_sub(m: "re.Match") -> str:
            attr = m.group(1)
            raw = m.group(2) if m.group(2) is not None else (
                m.group(3) if m.group(3) is not None else m.group(4)
            )
            absolute = _safe_url(final_url, raw)
            if not absolute:
                return m.group(0)
            rewritten = html_lib.escape(
                self._proxy_url(absolute, token, device_key, custom_ua), quote=True
            )
            original = html_lib.escape(absolute, quote=True)
            return f'{attr}="{rewritten}" data-ms-original="{original}"'

        body = _ATTR_RE.sub(_attr_sub, body)

        def _srcset_sub(m: "re.Match") -> str:
            attr, raw = m.group(1), m.group(2) if m.group(2) is not None else m.group(3)
            parts = []
            for item in raw.split(","):
                item = item.strip()
                if not item:
                    continue
                bits = item.split(None, 1)
                absolute = _safe_url(final_url, bits[0])
                if not absolute:
                    parts.append(item)
                    continue
                pu = html_lib.escape(self._proxy_url(absolute, token, device_key, custom_ua), quote=True)
                parts.append(pu + (" " + bits[1] if len(bits) > 1 else ""))
            return f'{attr}="' + ", ".join(parts) + '"'

        body = _SRCSET_RE.sub(_srcset_sub, body)

        def _refresh_sub(m: "re.Match") -> str:
            content = m.group(2)
            rm = re.search(r"(?i)url\s*=\s*['\"]?([^'\";\s>]+)", content)
            if not rm:
                return m.group(0)
            absolute = _safe_url(final_url, rm.group(1))
            if not absolute:
                return m.group(0)
            delay = content.split(";", 1)[0]
            pu = html_lib.escape(self._proxy_url(absolute, token, device_key, custom_ua), quote=True)
            return m.group(1) + delay + ";url=" + pu + m.group(3)

        body = _REFRESH_META_RE.sub(_refresh_sub, body)

        # <style> 内联样式里的 url()
        def _style_sub(m: "re.Match") -> str:
            return m.group(1) + self._rewrite_css(m.group(2), final_url, token, device_key, custom_ua) + m.group(3)

        body = re.sub(r"(?is)(<style[^>]*>)(.*?)(</style>)", _style_sub, body)

        bridge_cfg = {
            "baseUrl": final_url,
            "ua": ua,
            "platform": device["platform"],
            "vendor": device["vendor"],
            "device": device_key,
            "width": device["width"],
            "height": device["height"],
            "dpr": device["dpr"],
            "touch": bool(device["touch"]),
            "token": token,
            "uaCustom": custom_ua,
            "status": meta.get("status", 0),
            "elapsed": meta.get("elapsed", 0),
            "contentType": meta.get("content_type", ""),
        }
        bridge = _BRIDGE_JS.replace(
            "__MS_BRIDGE_CONFIG__",
            json.dumps(bridge_cfg, ensure_ascii=False).replace("<", "\\u003c"),
        )
        viewport = ('<meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width, initial-scale=1, '
                    'maximum-scale=5, viewport-fit=cover">')
        inject = viewport + "<script>" + bridge + "</script>"

        head = re.search(r"(?i)<head[^>]*>", body)
        if head:
            pos = head.end()
            return body[:pos] + "\n" + inject + "\n" + body[pos:]
        doctype = re.match(r"(?is)^\s*(<!doctype[^>]*>)", body)
        if doctype:
            pos = doctype.end()
            return body[:pos] + "\n<head>" + inject + "</head>\n" + body[pos:]
        return inject + "\n" + body

    def _cache_raw(self, url: str, resp: requests.Response, body: str, elapsed: int) -> None:
        with self._raw_lock:
            self._raw_cache[url] = {
                "status": resp.status_code,
                "final_url": resp.url,
                "elapsed": elapsed,
                "content_type": resp.headers.get("Content-Type", ""),
                "headers": dict(resp.headers),
                "html": body,
            }
            self._raw_cache.move_to_end(url)
            while len(self._raw_cache) > 20:
                self._raw_cache.popitem(last=False)

    def get_raw(self, url: str) -> Optional[Dict[str, Any]]:
        with self._raw_lock:
            return self._raw_cache.get(url)

    # ------------------------------------------------------------------ #
    # HTTP Handler
    # ------------------------------------------------------------------ #
    def _build_handler(self):
        from http.server import BaseHTTPRequestHandler

        sim = self

        class MobileSimulatorHandler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt, *args):
                pass

            # -------- 通用响应 -------- #
            def _send(self, status: int, data: bytes, ctype: str,
                      extra: Optional[Dict[str, str]] = None) -> None:
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    for k, v in (extra or {}).items():
                        self.send_header(k, v)
                    self.end_headers()
                    if self.command != "HEAD":
                        self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def _json(self, status: int, obj: Dict[str, Any]) -> None:
                self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                           "application/json; charset=utf-8")

            def _local_only(self) -> bool:
                host = (self.headers.get("Host") or "").split(":", 1)[0]
                return host in ("127.0.0.1", "localhost", "::1", "")

            def _error_html(self, title: str, message: str) -> bytes:
                page = (
                    "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
                    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                    "<style>body{font:14px/1.7 -apple-system,'PingFang SC',sans-serif;"
                    "background:#fff;color:#24292f;padding:24px;margin:0}"
                    "h3{margin:0 0 12px;color:#cf222e}pre{white-space:pre-wrap;word-break:break-all;"
                    "background:#f6f8fa;padding:14px;border-radius:8px;font-size:12px}"
                    "p{color:#57606a}</style></head><body>"
                    f"<h3>📱 {html_lib.escape(title)}</h3>"
                    f"<pre>{html_lib.escape(message)}</pre>"
                    "<p>可在上方地址栏换一个网址，或在右侧切换设备预设 / 自定义 UA 后刷新。</p>"
                    "<script>parent.postMessage({type:'ms-loaded',url:'',status:0,"
                    "elapsed:0,contentType:'',title:'加载失败'},'*');</script>"
                    "</body></html>"
                )
                return page.encode("utf-8")

            def _shell(self) -> None:
                cfg = {
                    "token": sim.token,
                    "devices": DEVICE_PRESETS,
                    "defaultDevice": sim.default_device,
                    "defaultUA": "",
                    "defaultUrl": sim.start_url,
                    "scale": 1,
                }
                page = _SHELL_HTML.replace(
                    "__MS_SHELL_CONFIG__",
                    json.dumps(cfg, ensure_ascii=False).replace("<", "\\u003c"),
                )
                self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")

            # -------- 请求分发 -------- #
            def do_GET(self) -> None:
                if not self._local_only():
                    self._json(403, {"error": "仅允许本机访问"})
                    return
                parsed = urlparse(self.path)
                path, query = parsed.path, parse_qs(parsed.query)

                if path in ("/", "/index.html", "/mobile", "/mobile/"):
                    self._shell()
                    return
                if path == "/health":
                    self._json(200, {"status": "ok", "port": sim.port})
                    return
                if path == "/favicon.ico":
                    self._send(204, b"", "image/x-icon")
                    return
                if path == "/raw":
                    self._handle_raw(query)
                    return
                if path == "/proxy":
                    self._handle_proxy(query, "GET", b"")
                    return
                self._send(404, b"Not Found", "text/plain; charset=utf-8")

            def do_POST(self) -> None:
                if not self._local_only():
                    self._json(403, {"error": "仅允许本机访问"})
                    return
                parsed = urlparse(self.path)
                if parsed.path != "/proxy":
                    self._send(404, b"Not Found", "text/plain; charset=utf-8")
                    return
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    length = 0
                body = self.rfile.read(length) if length > 0 else b""
                self._handle_proxy(parse_qs(parsed.query), "POST", body)

            def do_OPTIONS(self) -> None:
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Content-Length", "0")
                self.end_headers()

            # -------- 源码 -------- #
            def _handle_raw(self, query) -> None:
                if query.get("t", [""])[0] != sim.token:
                    self._json(403, {"error": "无效的会话令牌"})
                    return
                url = query.get("url", [""])[0]
                cached = sim.get_raw(url)
                if cached:
                    self._json(200, cached)
                    return
                device = query.get("d", [DEFAULT_DEVICE])[0]
                ua = query.get("ua", [""])[0]
                try:
                    started = time.time()
                    resp = sim.fetch(url, device, ua)
                    elapsed = int((time.time() - started) * 1000)
                    if resp is None:
                        self._json(502, {"error": "抓取失败"})
                        return
                    body = _decode_body(resp)
                    sim._cache_raw(url, resp, body, elapsed)
                    self._json(200, sim.get_raw(url) or {"error": "无内容"})
                except Exception as e:
                    self._json(502, {"error": str(e)})

            # -------- 代理 -------- #
            def _handle_proxy(self, query, method: str, body: bytes) -> None:
                if query.get("t", [""])[0] != sim.token:
                    self._send(403, self._error_html("令牌无效", "请从手机模拟器页面重新打开，不要直接访问 /proxy。"),
                               "text/html; charset=utf-8")
                    return
                url = query.get("url", [""])[0]
                if not url:
                    self._send(400, self._error_html("缺少网址", "请求未包含 url 参数。"),
                               "text/html; charset=utf-8")
                    return
                device = query.get("d", [DEFAULT_DEVICE])[0]
                if device not in DEVICE_PRESETS:
                    device = DEFAULT_DEVICE
                custom_ua = query.get("ua", [""])[0]

                # GET 表单提交：把附加字段合并进目标网址
                if method == "GET":
                    extra = {k: v[-1] for k, v in query.items()
                             if k not in ("url", "t", "d", "ua", "dl", "_")}
                    if extra:
                        sep = "&" if urlparse(url).query else "?"
                        url = url + sep + urlencode(extra)

                started = time.time()
                try:
                    resp = sim.fetch(url, device, custom_ua, method, body,
                                     self.headers.get("Content-Type", ""))
                except ValueError as e:
                    self._send(400, self._error_html("网址不合法", str(e)),
                               "text/html; charset=utf-8")
                    return
                except requests.RequestException as e:
                    msg = (f"目标网址：{url}\n\n错误：{e}\n\n"
                           "可尝试：切换设备预设（不同 UA）、自定义 UA、检查网络或代理设置、"
                           "或在系统浏览器里确认该站点是否可访问。")
                    self._send(502, self._error_html("抓取失败", msg),
                               "text/html; charset=utf-8")
                    return
                except Exception as e:
                    self._send(502, self._error_html("抓取失败", f"{url}\n\n{e}"),
                               "text/html; charset=utf-8")
                    return
                if resp is None:
                    self._send(502, self._error_html("抓取失败", url),
                               "text/html; charset=utf-8")
                    return

                elapsed = int((time.time() - started) * 1000)
                ctype = resp.headers.get("Content-Type", "") or ""
                try:
                    ctype.encode("latin-1")
                except UnicodeEncodeError:
                    ctype = ""
                if not ctype.strip():
                    ctype = "application/octet-stream"
                ctype_lower = ctype.lower()
                mime = ctype_lower.split(";", 1)[0].strip()
                disposition = resp.headers.get("Content-Disposition", "") or ""
                raw = resp.content or b""
                final_url = resp.url or url
                filename = _suggested_filename(final_url, disposition)

                # Sec-Fetch-Dest 由浏览器发出：只有文档/iframe 导航会把响应当"页面"，
                # 图片、脚本等子资源即便缺少 Content-Type 也应原样透传。
                dest = (self.headers.get("Sec-Fetch-Dest") or "").lower()
                is_navigation = dest in ("", "document", "iframe", "frame")
                allow_download = query.get("dl", [""])[0] == "1"
                is_html_type = ("text/html" in ctype_lower
                                or "application/xhtml+xml" in ctype_lower
                                or "text/vnd.wap.wml" in ctype_lower)
                is_css_type = "text/css" in ctype_lower
                looks_html = _looks_like_html(raw)
                is_download = (_is_download_mime(mime)
                               or "attachment" in disposition.lower())

                extra_headers = {
                    # header 只能是 latin-1，URL 里的非 ASCII 字符必须转义
                    "X-MS-Final-Url": quote(final_url, safe=""),
                    "X-MS-Status": str(resp.status_code),
                    "X-MS-Elapsed": str(elapsed),
                }
                try:
                    set_cookies = resp.raw.headers.getlist("Set-Cookie")
                except Exception:
                    set_cookies = []

                if is_css_type:
                    css = _decode_body(resp)
                    data = sim._rewrite_css(css, final_url, sim.token,
                                            device, custom_ua).encode("utf-8")
                    out_type = "text/css; charset=utf-8"
                elif is_html_type or looks_html:
                    # 内容是 HTML/WML 就正常渲染，哪怕站点把 Content-Type 写错或没写。
                    text = _decode_body(resp)
                    sim._cache_raw(url, resp, text, elapsed)
                    meta = {"status": resp.status_code, "elapsed": elapsed, "content_type": ctype}
                    out = sim._rewrite_html(text, final_url, device, custom_ua,
                                            sim.token, meta)
                    data = out.encode("utf-8")
                    out_type = "text/html; charset=utf-8"
                elif is_download and is_navigation and not allow_download:
                    logger.info(f"[手机模拟器] 已拦截文档导航的下载类响应: {final_url} "
                                f"({ctype}, {len(raw)} bytes)")
                    dl_url = sim._proxy_url(final_url, sim.token, device, custom_ua) + "&dl=1"
                    data = _download_notice_html(final_url, filename, ctype,
                                                 len(raw), elapsed, dl_url)
                    out_type = "text/html; charset=utf-8"
                else:
                    data = raw
                    out_type = ctype
                    if is_download and allow_download:
                        # 用户明确要求下载时，带回真实文件名，而不是让浏览器按 /proxy 命名。
                        safe_name = re.sub(r'[\r\n"]', "", filename) or "download"
                        ascii_name = safe_name.encode("ascii", "ignore").decode("ascii") or "download"
                        extra_headers["Content-Disposition"] = (
                            f'attachment; filename="{ascii_name}"; '
                            f"filename*=UTF-8''{quote(safe_name, safe='')}"
                        )

                # 逐个发送 Set-Cookie（BaseHTTPRequestHandler 不支持同名多值合并）
                self.send_response(200)
                self.send_header("Content-Type", out_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                for k, v in extra_headers.items():
                    self.send_header(k, v)
                for raw_cookie in set_cookies:
                    cleaned = re.sub(r"(?i);\s*domain=[^;]*", "", raw_cookie)
                    cleaned = re.sub(r"(?i);\s*secure\b", "", cleaned)
                    cleaned = re.sub(r"(?i);\s*samesite=[^;]*", "", cleaned)
                    try:
                        cleaned.encode("latin-1")
                    except UnicodeEncodeError:
                        continue
                    self.send_header("Set-Cookie", cleaned)
                self.end_headers()
                try:
                    if self.command != "HEAD":
                        self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        return MobileSimulatorHandler


# --------------------------------------------------------------------------- #
# 对外便捷入口
# --------------------------------------------------------------------------- #
def get_mobile_simulator() -> MobileSimulator:
    return MobileSimulator.get_instance()


def open_mobile_simulator(url: str = "", device: str = "", ua: str = "") -> Tuple[bool, str]:
    """打开 HTML 手机模拟器。url 会以 ?url= 参数传入页面。"""
    return MobileSimulator.get_instance().open(url, device, ua)


def build_mobile_simulator_url(url: str = "", device: str = "", ua: str = "") -> str:
    """仅返回带网址参数的模拟器地址（不打开浏览器）。"""
    return MobileSimulator.get_instance().build_page_url(url, device, ua)
