"""
浏览器文本编辑器

启动一个本地 HTTP 服务（仅监听 127.0.0.1），提供功能全面的纯前端文本编辑器，
用于在浏览器中编辑书籍文本文件。编辑器完全离线（不依赖任何外部 CDN），
支持：行号、查找/替换、撤销/重做、自动换行、字体缩放、全屏、Markdown 快捷插入、
字数/行数统计、自动保存、下载副本等。

用法：
    from src.utils.browser_editor import BrowserEditorServer
    url = BrowserEditorServer("/path/to/book.md").start()
    # 使用系统设置中指定的浏览器打开（遵循 browser.default_browser）
    open_in_browser(url)
"""

import json
import os
import threading
import time
import secrets
import webbrowser
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from typing import Optional

logger = logging.getLogger(__name__)


def open_in_browser(url: str) -> None:
    """使用系统设置中指定的浏览器打开编辑器 URL

    优先使用 BrowserManager（遵循配置 browser.default_browser），
    失败时回退到系统默认浏览器（webbrowser）。
    """
    try:
        from src.utils.browser_manager import BrowserManager
        if BrowserManager.open_url(url):
            return
    except Exception as e:
        logger.warning(f"使用 BrowserManager 打开浏览器失败，回退到系统默认浏览器: {e}")
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.error(f"打开浏览器失败: {e}")


# ----------------------------------------------------------------------
# 编辑器页面模板（纯前端，无外部依赖）
# ----------------------------------------------------------------------
EDITOR_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>浏览器文本编辑器</title>
<style>
  :root {
    --bg: #1e1e2e;
    --bg2: #181825;
    --bg3: #11111b;
    --panel: #313244;
    --border: #45475a;
    --text: #cdd6f4;
    --muted: #9399b2;
    --accent: #89b4fa;
    --green: #a6e3a1;
    --red: #f38ba8;
    --yellow: #f9e2af;
    --mauve: #cba6f7;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; height: 100%; background: var(--bg3); color: var(--text);
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
    font-size: 14px; overflow: hidden;
  }
  #app { display: flex; flex-direction: column; height: 100vh; }
  .toolbar {
    display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
    padding: 8px 10px; background: var(--bg2); border-bottom: 1px solid var(--border);
  }
  .toolbar .sep { width: 1px; height: 22px; background: var(--border); margin: 0 4px; }
  button {
    background: var(--panel); color: var(--text); border: 1px solid var(--border);
    border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 13px;
    transition: background .15s, border-color .15s;
  }
  button:hover { background: var(--border); }
  button:active { transform: translateY(1px); }
  button.primary { background: #4579c4; border-color: #5a8fd6; color: #fff; }
  button.primary:hover { background: #5a8fd6; }
  button.warn { background: #b4524f; border-color: #d36b68; color: #fff; }
  button.warn:hover { background: #d36b68; }
  .md-bar {
    display: flex; flex-wrap: wrap; align-items: center; gap: 4px;
    padding: 6px 10px; background: var(--bg2); border-bottom: 1px solid var(--border);
  }
  .md-bar button { padding: 4px 8px; font-size: 12px; }
  .find-bar {
    display: none; align-items: center; gap: 6px; flex-wrap: wrap;
    padding: 6px 10px; background: var(--bg2); border-bottom: 1px solid var(--border);
  }
  .find-bar.show { display: flex; }
  .find-bar input {
    background: var(--bg3); color: var(--text); border: 1px solid var(--border);
    border-radius: 5px; padding: 5px 8px; font-size: 13px; min-width: 180px;
  }
  .find-info { color: var(--muted); margin-left: 8px; font-size: 12px; }
  #editor-wrap {
    flex: 1; display: flex; min-height: 0; background: var(--bg); position: relative;
  }
  #gutter {
    flex: 0 0 auto; min-width: 48px; padding: 8px 8px 8px 0; text-align: right;
    background: var(--bg3); color: var(--muted); overflow: hidden; user-select: none;
    font-family: "JetBrains Mono", "Consolas", "Menlo", monospace; font-size: 14px;
    line-height: 22px; white-space: pre; border-right: 1px solid var(--border);
  }
  #editor {
    flex: 1; resize: none; border: none; outline: none; padding: 8px 12px;
    background: var(--bg); color: var(--text);
    font-family: "JetBrains Mono", "Consolas", "Menlo", monospace; font-size: 14px;
    line-height: 22px; white-space: pre; overflow: auto; tab-size: 4;
  }
  #editor.wrap { white-space: pre-wrap; word-break: break-word; }
  .statusbar {
    display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
    padding: 6px 12px; background: var(--bg2); border-top: 1px solid var(--border);
    color: var(--muted); font-size: 12px;
  }
  .statusbar .spacer { flex: 1; }
  .statusbar .ok { color: var(--green); }
  .statusbar .dirty { color: var(--yellow); }
  .statusbar .saving { color: var(--accent); }
  .statusbar .err { color: var(--red); }
  #toast {
    position: fixed; top: 22px; left: 50%; transform: translateX(-50%) translateY(-14px);
    z-index: 2147483640; max-width: 80vw; padding: 13px 26px; border-radius: 12px;
    font-size: 16px; font-weight: 700; color: #fff; letter-spacing: .5px;
    box-shadow: 0 10px 30px rgba(0,0,0,.4); opacity: 0; pointer-events: none;
    transition: opacity .28s ease, transform .28s ease; display: flex; align-items: center; gap: 10px;
  }
  #toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
  #toast.ok { background: linear-gradient(135deg,#27ae60,#1e8e4f); }
  #toast.err { background: linear-gradient(135deg,#e74c3c,#c0392b); }
  #toast.info { background: linear-gradient(135deg,#4579c4,#345fa0); }
  #edit-col { flex: 1; display: flex; min-width: 0; min-height: 0; }
  #preview {
    display: none; flex: 1; overflow: auto; padding: 12px 18px;
    background: var(--bg); border-left: 1px solid var(--border);
    color: var(--text); line-height: 1.7; font-size: 15px;
  }
  #editor-wrap.show-preview #preview { display: block; }
  #preview h1, #preview h2, #preview h3, #preview h4, #preview h5, #preview h6 {
    color: var(--text); margin: 0.8em 0 0.4em; line-height: 1.3;
  }
  #preview h1 { font-size: 1.8em; border-bottom: 1px solid var(--border); padding-bottom: 0.2em; }
  #preview h2 { font-size: 1.5em; }
  #preview h3 { font-size: 1.3em; }
  #preview p { margin: 0.6em 0; }
  #preview a { color: var(--accent); }
  #preview blockquote {
    margin: 0.6em 0; padding: 0.4em 1em; border-left: 3px solid var(--accent);
    background: var(--bg2); color: var(--muted);
  }
  #preview code {
    background: var(--bg3); padding: 1px 5px; border-radius: 4px;
    font-family: "JetBrains Mono", "Consolas", monospace; font-size: 0.92em;
  }
  #preview pre.md-code {
    background: var(--bg3); padding: 10px 12px; border-radius: 6px; overflow: auto;
    border: 1px solid var(--border);
  }
  #preview pre.md-code code { background: none; padding: 0; }
  #preview ul, #preview ol { margin: 0.5em 0; padding-left: 1.6em; }
  #preview li { margin: 0.2em 0; }
  #preview hr { border: none; border-top: 1px solid var(--border); margin: 1em 0; }
  #preview img { max-width: 100%; }
</style>
</head>
<body>
<div id="app">
  <div class="toolbar">
    <button id="btn-save" class="primary">保存 (Ctrl+S)</button>
    <button id="btn-find">查找 / 替换</button>
    <span class="sep"></span>
    <button id="btn-undo">撤销</button>
    <button id="btn-redo">重做</button>
    <span class="sep"></span>
    <button id="btn-wrap" class="primary">自动换行</button>
    <button id="btn-font-down">A-</button>
    <button id="btn-font-up">A+</button>
    <button id="btn-fullscreen">全屏</button>
    <button id="btn-preview">预览</button>
    <span class="sep"></span>
    <button id="btn-download">下载副本</button>
    <button id="btn-reload">重新加载</button>
    <button id="btn-return" class="primary" style="display:none;">返回阅读</button>
    <button id="btn-close" class="warn">关闭编辑器</button>
  </div>

  <div class="md-bar">
    <span style="color:var(--muted);font-size:12px;margin-right:4px;">格式：</span>
    <button data-md="h1">H1</button>
    <button data-md="h2">H2</button>
    <button data-md="h3">H3</button>
    <button data-md="bold">粗体</button>
    <button data-md="italic">斜体</button>
    <button data-md="strike">删除线</button>
    <button data-md="quote">引用</button>
    <button data-md="ul">列表</button>
    <button data-md="ol">有序列表</button>
    <button data-md="code">代码</button>
    <button data-md="link">链接</button>
    <button data-md="hr">分隔线</button>
    <button data-md="indent">缩进</button>
    <button data-md="outdent">反缩进</button>
  </div>

  <div class="find-bar" id="find-bar">
    <input id="find-input" placeholder="查找内容">
    <button id="find-prev">上一个</button>
    <button id="find-next">下一个</button>
    <span class="find-info" id="find-info"></span>
    <span class="sep"></span>
    <input id="replace-input" placeholder="替换为">
    <button id="replace-one">替换</button>
    <button id="replace-all">全部替换</button>
    <label style="color:var(--muted);font-size:12px;">
      <input type="checkbox" id="find-case"> 区分大小写
    </label>
    <button id="find-close">关闭</button>
  </div>

  <div id="editor-wrap">
    <div id="edit-col">
      <div id="gutter">1</div>
      <textarea id="editor" class="wrap" spellcheck="false" placeholder="在此编辑文本…"></textarea>
    </div>
    <div id="preview"></div>
  </div>

  <div class="statusbar">
    <span id="st-chars">字符数: 0</span>
    <span id="st-words">词数: 0</span>
    <span id="st-lines">行数: 1</span>
    <span id="st-cursor">行: 1, 列: 1</span>
    <span id="st-encode">编码: UTF-8</span>
    <span class="spacer"></span>
    <span id="st-save" class="ok">已加载</span>
  </div>
  <div id="toast"></div>
</div>

<script>
(function () {
  "use strict";
  var TOKEN = "__TOKEN__";
  var SAVE_URL = "/api/save?token=" + TOKEN;
  var CONTENT_URL = "/api/content?token=" + TOKEN;
  var CLOSE_URL = "/api/close?token=" + TOKEN;
  var RETURN_URL = (new URLSearchParams(location.search).get("return")) || "";
  var HAS_OPENER = !!window.opener;
  // 是否作为阅读器内的浮层（iframe）打开：是则通过 postMessage 通知父页关闭浮层
  var EMBEDDED = (window.self !== window.top);

  var editor = document.getElementById("editor");
  var gutter = document.getElementById("gutter");
  var stChars = document.getElementById("st-chars");
  var stWords = document.getElementById("st-words");
  var stLines = document.getElementById("st-lines");
  var stCursor = document.getElementById("st-cursor");
  var stSave = document.getElementById("st-save");

  var initialContent = __CONTENT__;
  editor.value = initialContent;

  var dirty = false;
  var lastSavedContent = initialContent;
  var fontSize = 14;
  var findMatches = [];
  var findIndex = -1;
  var previewOn = false;

  // ---------- 行号 ----------
  function updateGutter() {
    var lines = editor.value.split("\n").length;
    var s = "";
    for (var i = 1; i <= lines; i++) s += i + "\n";
    gutter.textContent = s;
    editor.scrollTop = editor.scrollTop; // keep
    gutter.scrollTop = editor.scrollTop;
  }

  // ---------- 统计 ----------
  function updateStats() {
    var v = editor.value;
    stChars.textContent = "字符数: " + v.length;
    var cjk = (v.match(/[一-鿿]/g) || []).length;
    var words = (v.match(/[A-Za-z0-9_]+/g) || []).length;
    stWords.textContent = "词数: " + (cjk + words);
    stLines.textContent = "行数: " + (v.split("\n").length);
    var pos = getCursorLineCol();
    stCursor.textContent = "行: " + pos.line + ", 列: " + pos.col;
  }

  function getCursorLineCol() {
    var idx = editor.selectionStart;
    var before = editor.value.slice(0, idx);
    var line = before.split("\n").length;
    var col = idx - before.lastIndexOf("\n");
    return { line: line, col: col };
  }

  function setSaveState(cls, text) {
    stSave.className = cls;
    stSave.textContent = text;
  }

  // 醒目提示横幅（顶部居中，自动消失）
  var toastEl = document.getElementById("toast");
  var toastTimer = null;
  function showToast(text, type) {
    type = type || "ok";
    toastEl.className = type + " show";
    toastEl.textContent = text;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.className = type; }, 2200);
  }

  function markDirty() {
    if (!dirty) { dirty = true; }
    setSaveState("dirty", "● 未保存");
    scheduleAutoSave();
  }

  // ---------- 撤销 / 重做 ----------
  var undoStack = [], redoStack = [], snapshotTimer = null, lastSnapshot = editor.value;
  function snapshot() {
    if (lastSnapshot === editor.value) return;
    undoStack.push(lastSnapshot);
    if (undoStack.length > 80) undoStack.shift();
    redoStack = [];
    lastSnapshot = editor.value;
  }
  function onInputDebounced() {
    if (snapshotTimer) clearTimeout(snapshotTimer);
    snapshotTimer = setTimeout(snapshot, 400);
    updateGutter(); updateStats(); markDirty();
    if (previewOn) renderPreview();
  }
  function doUndo() {
    if (!undoStack.length) return;
    redoStack.push(editor.value);
    editor.value = undoStack.pop();
    lastSnapshot = editor.value;
    updateGutter(); updateStats(); markDirty(); setCursorEnd();
  }
  function doRedo() {
    if (!redoStack.length) return;
    undoStack.push(editor.value);
    editor.value = redoStack.pop();
    lastSnapshot = editor.value;
    updateGutter(); updateStats(); markDirty(); setCursorEnd();
  }
  function setCursorEnd() {
    var n = editor.value.length;
    editor.selectionStart = editor.selectionEnd = n;
  }

  // ---------- 保存 ----------
  var saveTimer = null;
  function scheduleAutoSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(function () { save(false); }, 5000);
  }
  function save(showNotify) {
    var content = editor.value;
    setSaveState("saving", "保存中…");
    fetch(SAVE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: content })
    }).then(function (r) { return r.json();     }).then(function (d) {
      if (d.success) {
        dirty = false; lastSavedContent = content;
        var t = new Date().toLocaleTimeString();
        setSaveState("ok", "已保存 " + t);
        if (showNotify) showToast("✓ 已保存  " + t, "ok");
      } else {
        setSaveState("err", "保存失败: " + (d.error || "未知错误"));
        if (showNotify) showToast("✗ 保存失败：" + (d.error || "未知错误"), "err");
      }
    }).catch(function (e) {
      setSaveState("err", "保存失败: " + e);
      if (showNotify) showToast("✗ 保存失败：" + e, "err");
    });
  }

  // ---------- 重新加载 ----------
  function reload() {
    if (dirty && !confirm("有未保存的修改，确定重新加载（将丢失修改）吗？")) return;
    fetch(CONTENT_URL).then(function (r) { return r.json(); }).then(function (d) {
      editor.value = d.content || "";
      lastSnapshot = editor.value; lastSavedContent = editor.value; dirty = false;
      updateGutter(); updateStats(); setSaveState("ok", "已重新加载");
    });
  }

  // ---------- Tab 键插入空格 ----------
  function handleTab(e) {
    if (e.key === "Tab") {
      e.preventDefault();
      var s = editor.selectionStart, en = editor.selectionEnd;
      var pad = "    ";
      if (e.shiftKey) {
        // 反缩进：删除行首最多4个空格
        var lineStart = editor.value.lastIndexOf("\n", s - 1) + 1;
        var head = editor.value.slice(lineStart, lineStart + 4);
        var remove = 0;
        while (remove < head.length && head[remove] === " ") remove++;
        if (remove > 0) {
          editor.value = editor.value.slice(0, lineStart) + editor.value.slice(lineStart + remove);
          editor.selectionStart = editor.selectionEnd = Math.max(lineStart, s - remove);
        }
      } else {
        editor.value = editor.value.slice(0, s) + pad + editor.value.slice(en);
        editor.selectionStart = editor.selectionEnd = s + pad.length;
      }
      onInputDebounced();
    }
  }

  // ---------- 查找 / 替换 ----------
  function buildMatches() {
    var q = document.getElementById("find-input").value;
    findMatches = [];
    findIndex = -1;
    if (!q) { updateFindInfo(); return; }
    var v = editor.value;
    var caseSensitive = document.getElementById("find-case").checked;
    var flags = caseSensitive ? "g" : "gi";
    var re;
    try { re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), flags); }
    catch (e) { updateFindInfo(); return; }
    var m;
    while ((m = re.exec(v)) !== null) {
      findMatches.push(m.index);
      if (m.index === re.lastIndex) re.lastIndex++;
      if (findMatches.length > 10000) break;
    }
    updateFindInfo();
  }
  function updateFindInfo() {
    var el = document.getElementById("find-info");
    if (!findMatches.length) { el.textContent = "无匹配"; return; }
    if (findIndex < 0) findIndex = 0;
    el.textContent = (findIndex + 1) + " / " + findMatches.length;
    selectMatch(findMatches[findIndex]);
  }
  function selectMatch(idx) {
    var q = document.getElementById("find-input").value;
    if (!q) return;
    var s = editor.selectionStart, en = editor.selectionEnd;
    editor.focus();
    editor.setSelectionRange(idx, idx + q.length);
    // 滚动到可见
    var line = editor.value.slice(0, idx).split("\n").length;
    editor.scrollTop = Math.max(0, (line - 5) * 22);
    gutter.scrollTop = editor.scrollTop;
  }
  function findNext() {
    if (!findMatches.length) { buildMatches(); if (!findMatches.length) return; }
    findIndex = (findIndex + 1) % findMatches.length;
    updateFindInfo();
  }
  function findPrev() {
    if (!findMatches.length) { buildMatches(); if (!findMatches.length) return; }
    findIndex = (findIndex - 1 + findMatches.length) % findMatches.length;
    updateFindInfo();
  }
  function replaceOne() {
    if (findIndex < 0 || !findMatches.length) return;
    var q = document.getElementById("find-input").value;
    var rep = document.getElementById("replace-input").value;
    var idx = findMatches[findIndex];
    editor.value = editor.value.slice(0, idx) + rep + editor.value.slice(idx + q.length);
    buildMatches();
    onInputDebounced();
  }
  function replaceAll() {
    var q = document.getElementById("find-input").value;
    var rep = document.getElementById("replace-input").value;
    if (!q) return;
    var caseSensitive = document.getElementById("find-case").checked;
    var flags = caseSensitive ? "g" : "gi";
    var re;
    try { re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), flags); }
    catch (e) { return; }
    editor.value = editor.value.replace(re, rep);
    buildMatches();
    onInputDebounced();
  }

  // ---------- Markdown 快捷插入 ----------
  function wrapSelection(before, after) {
    var s = editor.selectionStart, en = editor.selectionEnd;
    var sel = editor.value.slice(s, en);
    var text = before + sel + after;
    editor.value = editor.value.slice(0, s) + text + editor.value.slice(en);
    editor.focus();
    editor.selectionStart = s + before.length;
    editor.selectionEnd = s + before.length + sel.length;
    onInputDebounced();
  }
  function prefixLines(prefix) {
    var s = editor.selectionStart, en = editor.selectionEnd;
    var lineStart = editor.value.lastIndexOf("\n", s - 1) + 1;
    var seg = editor.value.slice(lineStart, en);
    var replaced = seg.split("\n").map(function (l) { return prefix + l; }).join("\n");
    editor.value = editor.value.slice(0, lineStart) + replaced + editor.value.slice(en);
    editor.focus();
    editor.selectionStart = lineStart;
    editor.selectionEnd = lineStart + replaced.length;
    onInputDebounced();
  }
  function handleMd(type) {
    if (type === "h1") prefixLines("# ");
    else if (type === "h2") prefixLines("## ");
    else if (type === "h3") prefixLines("### ");
    else if (type === "bold") wrapSelection("**", "**");
    else if (type === "italic") wrapSelection("*", "*");
    else if (type === "strike") wrapSelection("~~", "~~");
    else if (type === "quote") prefixLines("> ");
    else if (type === "ul") prefixLines("- ");
    else if (type === "ol") prefixLines("1. ");
    else if (type === "code") wrapSelection("`", "`");
    else if (type === "link") wrapSelection("[", "](https://)");
    else if (type === "hr") wrapSelection("\n", "\n---\n");
    else if (type === "indent") prefixLines("    ");
    else if (type === "outdent") {
      var s = editor.selectionStart, en = editor.selectionEnd;
      var lineStart = editor.value.lastIndexOf("\n", s - 1) + 1;
      var seg = editor.value.slice(lineStart, en);
      var replaced = seg.replace(/^( {1,4}|\t)/gm, "");
      editor.value = editor.value.slice(0, lineStart) + replaced + editor.value.slice(en);
      onInputDebounced();
    }
  }

  // ---------- 字体 / 换行 / 全屏 ----------
  function setFontSize(px) {
    fontSize = Math.max(10, Math.min(28, px));
    editor.style.fontSize = fontSize + "px";
    gutter.style.fontSize = fontSize + "px";
  }

  // ---------- 下载副本 ----------
  function download() {
    var blob = new Blob([editor.value], { type: "text/plain;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "book_copy.txt";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // ---------- 关闭 ----------
  function notifyParentClose() {
    try { parent.postMessage({ type: "br-editor-close" }, "*"); } catch (e) {}
  }
  function postClose() {
    if (!EMBEDDED) {
      // 通知后端关闭编辑器服务（浮层模式不关闭，服务随阅读会话长期持有）
      fetch(CLOSE_URL, { method: "POST" }).catch(function () {});
    }
    if (EMBEDDED) {
      // 以阅读器内浮层（iframe）形式打开：通知父页移除浮层，回到原阅读页
      notifyParentClose();
      return;
    }
    if (window.opener) {
      // 由阅读器通过 window.open 打开，可直接关闭本标签返回阅读页
      dirty = false;
      window.close();
      return;
    }
    // 独立打开（如从编辑弹窗启动）时脚本无法关闭标签，提示用户手动关闭
    setSaveState("ok", "编辑器已关闭，可关闭此标签页");
  }
  function closeEditor() {
    if (dirty && !confirm("有未保存的修改，确定关闭吗？")) return;
    postClose();
  }

  // ---------- Markdown 预览 ----------
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function inlineMd(s) {
    s = escapeHtml(s);
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    s = s.replace(/~~([^~]+)~~/g, "<del>$1</del>");
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return s;
  }
  function renderMarkdown(md) {
    var lines = md.replace(/\r\n/g, "\n").split("\n");
    var html = "", i = 0, inCode = false, codeBuf = [];
    function flushCode() {
      html += '<pre class="md-code"><code>' + escapeHtml(codeBuf.join("\n")) + "</code></pre>";
      codeBuf = [];
    }
    while (i < lines.length) {
      var line = lines[i];
      if (/^```/.test(line)) {
        if (inCode) { flushCode(); inCode = false; } else { inCode = true; }
        i++; continue;
      }
      if (inCode) { codeBuf.push(line); i++; continue; }
      var h = line.match(/^(#{1,6})\s+(.*)$/);
      if (h) { var lv = h[1].length; html += "<h" + lv + ">" + inlineMd(h[2]) + "</h" + lv + ">"; i++; continue; }
      if (/^(\*{3,}|_{3,}|-{3,})\s*$/.test(line)) { html += "<hr>"; i++; continue; }
      if (/^>\s?/.test(line)) {
        var q = [];
        while (i < lines.length && /^>\s?/.test(lines[i])) { q.push(lines[i].replace(/^>\s?/, "")); i++; }
        html += "<blockquote>" + renderMarkdown(q.join("\n")) + "</blockquote>";
        continue;
      }
      if (/^\s*[-*+]\s+/.test(line)) {
        var ul = [];
        while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) { ul.push("<li>" + inlineMd(lines[i].replace(/^\s*[-*+]\s+/, "")) + "</li>"); i++; }
        html += "<ul>" + ul.join("") + "</ul>";
        continue;
      }
      if (/^\s*\d+\.\s+/.test(line)) {
        var ol = [];
        while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) { ol.push("<li>" + inlineMd(lines[i].replace(/^\s*\d+\.\s+/, "")) + "</li>"); i++; }
        html += "<ol>" + ol.join("") + "</ol>";
        continue;
      }
      if (line.trim() === "") { i++; continue; }
      var para = [];
      while (i < lines.length && lines[i].trim() !== "" &&
             !/^(#{1,6})\s|^>\s?|^\s*[-*+]\s+|^\s*\d+\.\s+|^```|^(\*{3,}|_{3,}|-{3,})\s*$/.test(lines[i])) {
        para.push(lines[i]); i++;
      }
      html += "<p>" + para.map(inlineMd).join("<br>") + "</p>";
    }
    if (inCode) flushCode();
    return html;
  }
  function renderPreview() {
    var p = document.getElementById("preview");
    p.innerHTML = renderMarkdown(editor.value);
    p.scrollTop = 0;
  }
  function togglePreview() {
    previewOn = !previewOn;
    document.getElementById("editor-wrap").classList.toggle("show-preview", previewOn);
    document.getElementById("btn-preview").classList.toggle("primary", previewOn);
    if (previewOn) renderPreview();
  }

  // ---------- 事件绑定 ----------
  editor.addEventListener("input", onInputDebounced);
  editor.addEventListener("keyup", updateStats);
  editor.addEventListener("click", updateStats);
  editor.addEventListener("scroll", function () { gutter.scrollTop = editor.scrollTop; });
  editor.addEventListener("keydown", handleTab);

  document.getElementById("btn-save").onclick = function () { save(true); };
  document.getElementById("btn-undo").onclick = doUndo;
  document.getElementById("btn-redo").onclick = doRedo;
  document.getElementById("btn-wrap").onclick = function () {
    editor.classList.toggle("wrap");
    this.classList.toggle("primary");
  };
  document.getElementById("btn-font-up").onclick = function () { setFontSize(fontSize + 2); };
  document.getElementById("btn-font-down").onclick = function () { setFontSize(fontSize - 2); };
  document.getElementById("btn-fullscreen").onclick = function () {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen();
    else document.exitFullscreen();
  };
  document.getElementById("btn-download").onclick = download;
  document.getElementById("btn-reload").onclick = reload;
  document.getElementById("btn-close").onclick = closeEditor;
  document.getElementById("btn-preview").onclick = togglePreview;
  if (HAS_OPENER || EMBEDDED) {
    var btnReturnEl = document.getElementById("btn-return");
    btnReturnEl.style.display = "";
    btnReturnEl.onclick = function () {
      if (dirty && !confirm("有未保存的修改，确定返回阅读吗？")) return;
      postClose();
    };
  }

  document.getElementById("btn-find").onclick = function () {
    document.getElementById("find-bar").classList.add("show");
    document.getElementById("find-input").focus();
  };
  document.getElementById("find-close").onclick = function () {
    document.getElementById("find-bar").classList.remove("show");
  };
  document.getElementById("find-input").addEventListener("input", buildMatches);
  document.getElementById("find-next").onclick = findNext;
  document.getElementById("find-prev").onclick = findPrev;
  document.getElementById("replace-one").onclick = replaceOne;
  document.getElementById("replace-all").onclick = replaceAll;

  var mdButtons = document.querySelectorAll(".md-bar button");
  for (var i = 0; i < mdButtons.length; i++) {
    mdButtons[i].onclick = (function (b) {
      return function () { handleMd(b.getAttribute("data-md")); };
    })(mdButtons[i]);
  }

  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault(); save(true);
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
      e.preventDefault();
      document.getElementById("btn-find").click();
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !e.shiftKey) {
      e.preventDefault(); doUndo();
    } else if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey))) {
      e.preventDefault(); doRedo();
    }
  });

  window.addEventListener("beforeunload", function () {
    if (EMBEDDED) return;  // 浮层模式：关闭浮层不关闭服务、不提示
    if (dirty) {
      fetch(CLOSE_URL, { method: "POST" }).catch(function () {});
      return "有未保存的修改，确定离开吗？";
    }
    fetch(CLOSE_URL, { method: "POST" }).catch(function () {});
  });

  // 初始化
  updateGutter(); updateStats(); setSaveState("ok", "已加载");
})();
</script>
</body>
</html>
"""


class _EditorHandler(BaseHTTPRequestHandler):
    """浏览器编辑器请求处理器（由 start() 动态创建，可访问 server 上挂载的属性）"""

    def log_message(self, *args) -> None:  # 禁用请求日志
        pass

    # -- 工具方法 --
    def _send(self, code: int, body, content_type: str = "application/json; charset=utf-8") -> None:
        if isinstance(body, str):
            body = body.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            pass

    def _touch(self) -> None:
        try:
            self.server.last_activity = time.time()  # type: ignore[attr-defined]
        except Exception:
            pass

    def _check_token(self) -> bool:
        from urllib.parse import parse_qs
        q = parse_qs(urlparse(self.path).query)
        token = q.get("token", [""])[0]
        expected = getattr(self.server, "token", "")  # type: ignore[attr-defined]
        return token == expected

    def do_GET(self) -> None:  # noqa: N802
        self._touch()
        parsed = urlparse(self.path)
        if parsed.path == "/favicon.ico":
            self._send(204, b"")
        elif parsed.path in ("/", "/index.html"):
            try:
                with open(self.server.file_path, "r", encoding="utf-8") as f:  # type: ignore[attr-defined]
                    content = f.read()
            except Exception as e:
                content = ""
                logger.error(f"读取编辑文件失败: {e}")
            html = EDITOR_HTML.replace("__TOKEN__", self.server.token)  # type: ignore[attr-defined]
            html = html.replace("__CONTENT__", json.dumps(content).replace("</", "<\\/"))
            self._send(200, html, "text/html; charset=utf-8")
        elif parsed.path == "/api/content":
            if not self._check_token():
                self._send(401, json.dumps({"error": "invalid token"}))
                return
            try:
                with open(self.server.file_path, "r", encoding="utf-8") as f:  # type: ignore[attr-defined]
                    content = f.read()
                self._send(200, json.dumps({"content": content}, ensure_ascii=False))
            except Exception as e:
                self._send(500, json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self) -> None:  # noqa: N802
        self._touch()
        parsed = urlparse(self.path)
        if not self._check_token():
            self._send(401, json.dumps({"error": "invalid token"}))
            return
        if parsed.path == "/api/save":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode("utf-8")
                data = json.loads(raw)
                text = data.get("content", "")
            except Exception:
                text = ""
            try:
                with open(self.server.file_path, "w", encoding="utf-8") as f:  # type: ignore[attr-defined]
                    f.write(text)
                self._send(200, json.dumps({"success": True}, ensure_ascii=False))
                logger.info(f"浏览器编辑器已保存文件: {self.server.file_path}")  # type: ignore[attr-defined]
            except Exception as e:
                self._send(500, json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        elif parsed.path == "/api/close":
            self._send(200, json.dumps({"success": True}, ensure_ascii=False))
            threading.Thread(target=self.server.shutdown, daemon=True).start()  # type: ignore[attr-defined]
        else:
            self._send(404, json.dumps({"error": "not found"}))


class BrowserEditorServer:
    """本地浏览器编辑器服务（仅监听 127.0.0.1）"""

    def __init__(self, file_path: str, host: str = "127.0.0.1", idle_timeout: int = 1800):
        """
        Args:
            file_path: 要编辑的文件路径
            host: 监听地址（默认仅本机 127.0.0.1）
            idle_timeout: 空闲自动关闭时间（秒），默认 30 分钟
        """
        self.file_path = os.path.abspath(file_path)
        self.host = host
        self.idle_timeout = idle_timeout
        self.token = secrets.token_hex(8)
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> str:
        """启动服务并返回编辑器 URL"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

        server = ThreadingHTTPServer((self.host, 0), _EditorHandler)
        server.file_path = self.file_path  # type: ignore[attr-defined]
        server.token = self.token  # type: ignore[attr-defined]
        server.last_activity = time.time()  # type: ignore[attr-defined]
        port = server.server_address[1]
        self._server = server

        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()

        # 空闲看门狗：超过 idle_timeout 无活动则关闭
        watchdog = threading.Thread(target=self._watchdog, args=(server,), daemon=True)
        watchdog.start()

        url = f"http://{self.host}:{port}/?token={self.token}"
        logger.info(f"浏览器编辑器已启动: {url}")
        return url

    def _watchdog(self, server: ThreadingHTTPServer) -> None:
        if self.idle_timeout <= 0:
            return  # 0 或负数表示禁用空闲关闭（例如由阅读器长期持有）
        while True:
            time.sleep(30)
            try:
                if time.time() - getattr(server, "last_activity", time.time()) > self.idle_timeout:
                    logger.info("浏览器编辑器空闲超时，正在关闭服务")
                    server.shutdown()
                    break
            except Exception:
                break

    def stop(self) -> None:
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass


def open_book_in_browser_editor(file_path: str) -> Optional[str]:
    """便捷函数：启动浏览器编辑器并打开默认浏览器

    Returns:
        成功返回 URL，失败返回 None
    """
    try:
        server = BrowserEditorServer(file_path)
        url = server.start()
        open_in_browser(url)
        return url
    except Exception as e:
        logger.error(f"打开浏览器编辑器失败: {e}")
        return None
