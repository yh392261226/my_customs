package ui

import (
	"fmt"
	"strconv"
	"strings"
	"time"
	"ureader/config"

	"github.com/gdamore/tcell/v2"
	"github.com/rivo/tview"
)

// runTUIMode 运行TUI模式
func (ur *UnifiedReader) runTUIMode() error {
    app := tview.NewApplication()
    ur.tuiApp = app
    
    // 创建主界面
    mainUI := ur.createMainUI()
    
    // 创建终端模拟界面
    terminalUI := ur.createTerminalUI()
    
    // 创建页面容器
    pages := tview.NewPages().
        AddPage("main", mainUI, true, true).
        AddPage("terminal", terminalUI, true, false)
    
    ur.tuiPages = pages
    
    // 设置全局输入处理
    app.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
        // 检查是否处于隐藏状态
        currentPage, _ := pages.GetFrontPage()
        
        if currentPage == "terminal" {
            // 终端模式下的输入处理
            if event.Key() == tcell.KeyRune {
                switch event.Rune() {
                case 'i', 'I':
                    ur.toggleBossKey()
                    return nil
                }
            }
            // 其他按键传递给终端界面处理
            return event
        }
        
        // 主界面的输入处理
        if event.Key() == tcell.KeyRune {
            switch event.Rune() {
            case 'i', 'I':
                ur.toggleBossKey()
                return nil
            case ' ', 'n', 'N':
                if ur.currentPage < ur.totalPages-1 {
                    ur.nextPage()
                    ur.updateTUI()
                }
                return nil
            case 'p', 'P':
                if ur.currentPage > 0 {
                    ur.previousPage()
                    ur.updateTUI()
                }
                return nil
            case 'q', 'Q':
                app.Stop()
                return nil
            case 'g', 'G':
                ur.gotoPageTUI()
                return nil
            case 'm', 'M':
                ur.addBookmark()
                ur.showMessage("书签已添加")
                return nil
            case 'l', 'L':
                bookmarks := config.LoadBookmarks()
                var fileBookmarks []*config.Bookmark
                for _, bm := range bookmarks {
                    if bm.FilePath == ur.filePath {
                        fileBookmarks = append(fileBookmarks, bm)
                    }
                }
                ur.showBookmarksTUI(fileBookmarks)
                return nil
            case 's', 'S':
                ur.showSettingsTUI()
                return nil
            case '/':
                ur.searchTUI()
                return nil
            case 'r', 'R':
                ur.toggleReadAloud()
                return nil
            case 'a', 'A':
                ur.toggleAutoFlip()
                return nil
            case 'h', 'H', '?':
                ur.showHelpTUITUI()
                return nil
            case 'x', 'X':
                ur.showReadingStats()
                return nil
            case 'b', 'B':
                ur.toggleBookmark()
                return nil
            case 'f', 'F':
                ur.listBookmarks()
                return nil
            }
        }
        
        // 处理特殊按键
        switch event.Key() {
        case tcell.KeyRight:
            if ur.currentPage < ur.totalPages-1 {
                ur.nextPage()
                ur.updateTUI()
            }
            return nil
        case tcell.KeyLeft:
            if ur.currentPage > 0 {
                ur.previousPage()
                ur.updateTUI()
            }
            return nil
        case tcell.KeyHome:
            ur.firstPage()
            ur.updateTUI()
            return nil
        case tcell.KeyEnd:
            ur.lastPage()
            ur.updateTUI()
            return nil
        case tcell.KeyCtrlN:
            if ur.currentPage < ur.totalPages-1 {
                ur.nextPage()
                ur.updateTUI()
            }
            return nil
        case tcell.KeyCtrlP:
            if ur.currentPage > 0 {
                ur.previousPage()
                ur.updateTUI()
            }
            return nil
        }
        
        return event
    })
    
    // 启动自动翻页计时器（如果启用）
    if ur.config.AutoFlip {
        ur.startAutoFlipTUI(app)
    }
    
    return app.SetRoot(pages, true).SetFocus(ur.tuiTextView).Run()
}

// createMainUI 创建主界面
func (ur *UnifiedReader) createMainUI() *tview.Flex {
    // 创建TextView显示内容
    textView := tview.NewTextView().
        SetDynamicColors(true).
        SetRegions(true).
        SetWordWrap(true)
    
    // 设置内容
    textView.SetText(ur.getCurrentPageContent())
    
    // 创建标题栏和状态栏
    titleBar := createTitleBar(ur.fileName, ur.currentPage+1, ur.totalPages)
    statusBar := createStatusBar(ur.currentPage+1, ur.totalPages, ur.config.AutoFlip)
    
    // 创建主内容区域，应用padding
    contentBox := tview.NewFlex().
        SetDirection(tview.FlexRow).
        AddItem(nil, ur.config.Padding, 0, false). // 上padding
        AddItem(textView, 0, 1, true).
        AddItem(nil, ur.config.Padding, 0, false) // 下padding
    
    contentBoxWithPadding := tview.NewFlex().
        SetDirection(tview.FlexColumn).
        AddItem(nil, ur.config.Padding, 0, false). // 左padding
        AddItem(contentBox, 0, 1, true).
        AddItem(nil, ur.config.Padding, 0, false)  // 右padding
    
    // 创建主布局，应用margin
    mainFlex := tview.NewFlex().
        SetDirection(tview.FlexRow).
        AddItem(nil, ur.config.Margin, 0, false). // 上margin
        AddItem(titleBar, 1, 0, false).
        AddItem(contentBoxWithPadding, 0, 1, true).
        AddItem(statusBar, 1, 0, false).
        AddItem(nil, ur.config.Margin, 0, false) // 下margin
    
    mainFlexWithMargin := tview.NewFlex().
        SetDirection(tview.FlexColumn).
        AddItem(nil, ur.config.Margin, 0, false). // 左margin
        AddItem(mainFlex, 0, 1, true).
        AddItem(nil, ur.config.Margin, 0, false)  // 右margin
    
    // 设置边框
    if ur.config.BorderStyle != "none" {
        mainFlexWithMargin.SetBorder(true)
        mainFlexWithMargin.SetBorderColor(getTcellColor(ur.config.BorderColor))
        mainFlexWithMargin.SetTitle(fmt.Sprintf("《%s》", ur.fileName))
    }
    
    // 保存TUI组件的引用
    ur.tuiTextView = textView
    ur.tuiFlex = mainFlexWithMargin
    ur.tuiTitleBar = titleBar
    ur.tuiStatusBar = statusBar
    
    return mainFlexWithMargin
}

// createTerminalUI 创建终端模拟界面
func (ur *UnifiedReader) createTerminalUI() *tview.TextView {
    terminal := tview.NewTextView().
        SetDynamicColors(true).
        SetRegions(true).
        SetWordWrap(true)
    
    terminal.SetText("$ ")
    terminal.SetBorder(true).SetTitle("Terminal")
    
    // 设置终端输入处理
    terminal.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
        if event.Key() == tcell.KeyRune {
            switch event.Rune() {
            case 'i', 'I':
                ur.toggleBossKey()
                return nil
            case '\n', '\r':
                // 处理回车键
                currentText := terminal.GetText(false)
                lines := strings.Split(currentText, "\n")
                lastLine := lines[len(lines)-1]
                
                if strings.HasPrefix(lastLine, "$ ") {
                    command := strings.TrimPrefix(lastLine, "$ ")
                    result := ur.executeShellCommandTUI(command)
                    
                    if result != "" {
                        terminal.SetText(currentText + "\n" + result + "\n$ ")
                    } else {
                        terminal.SetText(currentText + "\n$ ")
                    }
                }
                return nil
            default:
                // 添加字符到终端
                currentText := terminal.GetText(false)
                terminal.SetText(currentText + string(event.Rune()))
            }
        } else if event.Key() == tcell.KeyBackspace || event.Key() == tcell.KeyBackspace2 {
            // 处理退格键
            currentText := terminal.GetText(false)
            if len(currentText) > 0 {
                terminal.SetText(currentText[:len(currentText)-1])
            }
        }
        return event
    })
    
    return terminal
}

// updateTUI 更新TUI界面
func (ur *UnifiedReader) updateTUI() {
    if ur.tuiTextView != nil {
        // 获取当前页面内容
        content := ur.getCurrentPageContent()
        
        // 应用文本换行处理，考虑padding和margin
        wrappedContent := ur.wrapTextForTUI(content)
        
        ur.tuiTextView.SetText(wrappedContent)
    }
    if ur.tuiTitleBar != nil {
        ur.tuiTitleBar.SetText(fmt.Sprintf("《%s》 - 第 %d/%d 页", 
            ur.fileName, ur.currentPage+1, ur.totalPages))
    }
    if ur.tuiStatusBar != nil {
        status := fmt.Sprintf("进度: %.1f%%", float64(ur.currentPage+1)/float64(ur.totalPages)*100)
        autoStatus := ""
        if ur.config.AutoFlip {
            autoStatus = " [自动翻页]"
        }
        help := "空格/→/n:下一页 ←/p:上一页 g:跳转 m:书签 /:搜索 r:朗读 a:自动翻页 q:退出"
        ur.tuiStatusBar.SetText(fmt.Sprintf("%s%s | %s", status, autoStatus, help))
    }
}

// wrapTextForTUI 为TUI模式包装文本
func (ur *UnifiedReader) wrapTextForTUI(text string) string {
    // 获取终端大小
    width, _, err := getTerminalSize() // 忽略高度，因为我们只需要宽度
    if err != nil {
        width = 80
    }
    
    // 计算可用宽度（减去margin和padding）
    availableWidth := width - 2*ur.config.Margin - 2*ur.config.Padding - 2 // 减去边框宽度
    
    // 如果可用宽度太小，使用最小宽度
    if availableWidth < 10 {
        availableWidth = 10
    }
    
    // 文本换行处理
    lines := strings.Split(text, "\n")
    var wrappedLines []string
    
    for _, line := range lines {
        if len(line) <= availableWidth {
            wrappedLines = append(wrappedLines, line)
        } else {
            // 需要换行
            for len(line) > availableWidth {
                wrappedLines = append(wrappedLines, line[:availableWidth])
                line = line[availableWidth:]
            }
            if len(line) > 0 {
                wrappedLines = append(wrappedLines, line)
            }
        }
    }
    
    return strings.Join(wrappedLines, "\n")
}

// startAutoFlipTUI 启动TUI模式的自动翻页
func (ur *UnifiedReader) startAutoFlipTUI(app *tview.Application) {
    ur.stopAutoFlip()
    
    // 确保间隔是正数
    if ur.config.AutoFlipInterval <= 0 {
        ur.config.AutoFlipInterval = 5 // 默认5秒
        config.SaveConfig(ur.config)
    }
    
    interval := time.Duration(ur.config.AutoFlipInterval) * time.Second
    ur.autoFlipTicker = time.NewTicker(interval)
    ur.autoFlipQuit = make(chan struct{})
    
    go func() {
        for {
            select {
            case <-ur.autoFlipTicker.C:
                app.QueueUpdateDraw(func() {
                    if ur.currentPage < ur.totalPages-1 {
                        ur.nextPage()
                        ur.updateTUI()
                    } else {
                        ur.stopAutoFlip()
                        // 更新配置状态
                        ur.config.AutoFlip = false
                        config.SaveConfig(ur.config)
                        // 更新状态栏
                        ur.updateTUI()
                    }
                })
            case <-ur.autoFlipQuit:
                return
            }
        }
    }()
}

// gotoPageTUI TUI模式的跳转页面
func (ur *UnifiedReader) gotoPageTUI() {
    // 创建输入框
    inputField := tview.NewInputField().
        SetLabel("页码: ").
        SetFieldWidth(10).
        SetAcceptanceFunc(tview.InputFieldInteger)
    
    // 设置输入框的回车处理
    inputField.SetDoneFunc(func(key tcell.Key) {
        if key == tcell.KeyEnter {
            pageStr := inputField.GetText()
            if pageStr != "" {
                if page, err := strconv.Atoi(pageStr); err == nil {
                    if page > 0 && page <= ur.totalPages {
                        ur.currentPage = page - 1
                        ur.updateTUI()
                        ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
                    } else {
                        // 页码超出范围
                        ur.showMessage(fmt.Sprintf("页码必须在 1 到 %d 之间", ur.totalPages))
                    }
                } else {
                    // 输入不是有效的数字
                    ur.showMessage("请输入有效的页码")
                }
            }
        } else if key == tcell.KeyEsc {
            // ESC键取消
            ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
        }
    })
    
    // 创建简单的布局
    flex := tview.NewFlex().
        SetDirection(tview.FlexRow).
        AddItem(inputField, 1, 0, true).
        AddItem(tview.NewTextView().SetText("按回车确认，按ESC取消"), 1, 0, false)
    
    flex.SetBorder(true).SetTitle("跳转到页面")
    
    // 设置模态为根页面
    ur.safeSetRoot(flex, inputField)
}

// showMessage 显示消息
func (ur *UnifiedReader) showMessage(message string) {
    // 只在TUI模式下使用模态对话框
    if ur.mode == ModeTUI && ur.tuiApp != nil {
        modal := tview.NewModal().
            SetText(message).
            AddButtons([]string{"确定"}).
            SetDoneFunc(func(buttonIndex int, buttonLabel string) {
                // 确保返回到正确的页面
                if ur.tuiPages != nil {
					ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
                }
            })
        
        // 设置ESC键处理
        modal.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
            if event.Key() == tcell.KeyEsc {
                ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
                return nil
            }
            return event
        })

        // 创建一个临时页面容器
        tempPages := tview.NewPages().
            AddPage("modal", modal, true, true)
        
        ur.safeSetRoot(tempPages, modal)
    } else {
        // 在其他模式下使用简单的控制台输出
        fmt.Println(message)
    }
}

// showBookmarksTUI TUI模式显示书签列表
func (ur *UnifiedReader) showBookmarksTUI(bookmarks []*config.Bookmark) {
    if len(bookmarks) == 0 {
        ur.showMessage("没有书签")
        return
    }
    
    list := tview.NewList().
        AddItem("返回", "返回阅读", 'b', func() {
            // 使用 safeSetRoot 返回主页面
            ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
        })
    
    for i, bm := range bookmarks {
        // 创建闭包内的局部变量
        bookmark := bm
        list.AddItem(
            fmt.Sprintf("%s (第%d页)", bookmark.Label, bookmark.Page+1),
            "跳转到此书签",
            rune('1'+i),
            func() {
                ur.currentPage = bookmark.Page
                ur.updateTUI()
                // 使用 safeSetRoot 返回主页面
                ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
            })
    }
    
    // 设置ESC键处理
    list.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
        if event.Key() == tcell.KeyEsc {
            ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
            return nil
        }
        return event
    })

    list.SetBorder(true).SetTitle("书签列表")
    
    // 创建一个新的页面容器
    pages := tview.NewPages().
        AddPage("bookmarks", list, true, true)
    
    // 设置输入处理
    pages.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
        switch event.Key() {
        case tcell.KeyEsc:
            // ESC键返回主页面
            ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
            return nil
        }
        return event
    })
    
    // 使用 safeSetRoot 设置新的根页面
    ur.safeSetRoot(pages, list)
}

// showSettingsTUI TUI模式显示设置
func (ur *UnifiedReader) showSettingsTUI() {
    form := tview.NewForm()
    
    // 字体颜色
    form.AddDropDown("字体颜色", []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"}, 
        getIndex(ur.config.FontColor, []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"}),
        func(option string, index int) {
            ur.config.FontColor = option
        })
    
    // 背景颜色
    form.AddDropDown("背景颜色", []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"}, 
        getIndex(ur.config.BackgroundColor, []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"}),
        func(option string, index int) {
            ur.config.BackgroundColor = option
        })
    
    // 边框颜色
    form.AddDropDown("边框颜色", []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "gray"}, 
        getIndex(ur.config.BorderColor, []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "gray"}),
        func(option string, index int) {
            ur.config.BorderColor = option
        })
    
    // 边框样式
    form.AddDropDown("边框样式", []string{"none", "single", "double", "round", "bold"}, 
        getIndex(ur.config.BorderStyle, []string{"none", "single", "double", "round", "bold"}),
        func(option string, index int) {
            ur.config.BorderStyle = option
        })
    
    // 宽度
    form.AddInputField("宽度", strconv.Itoa(ur.config.Width), 4, nil, func(text string) {
        if width, err := strconv.Atoi(text); err == nil && width > 0 {
            ur.config.Width = width
        }
    })
    
    // 高度
    form.AddInputField("高度", strconv.Itoa(ur.config.Height), 4, nil, func(text string) {
        if height, err := strconv.Atoi(text); err == nil && height > 0 {
            ur.config.Height = height
        }
    })
    
    // 边距
    form.AddInputField("边距", strconv.Itoa(ur.config.Margin), 2, nil, func(text string) {
        if margin, err := strconv.Atoi(text); err == nil && margin >= 0 {
            ur.config.Margin = margin
        }
    })
    
    // 内边距
    form.AddInputField("内边距", strconv.Itoa(ur.config.Padding), 2, nil, func(text string) {
        if padding, err := strconv.Atoi(text); err == nil && padding >= 0 {
            ur.config.Padding = padding
        }
    })
    
    // 朗读速度
    form.AddInputField("朗读速度", strconv.Itoa(ur.config.TTSSpeed), 2, nil, func(text string) {
        if speed, err := strconv.Atoi(text); err == nil && speed >= 1 && speed <= 10 {
            ur.config.TTSSpeed = speed
        }
    })
    
    // 自动朗读
    form.AddCheckbox("自动朗读", ur.config.AutoReadAloud, func(checked bool) {
        ur.config.AutoReadAloud = checked
    })
    
    // 自动翻页
    form.AddCheckbox("自动翻页", ur.config.AutoFlip, func(checked bool) {
        ur.config.AutoFlip = checked
    })
    
    // 自动翻页间隔
    form.AddInputField("自动翻页间隔(秒)", strconv.Itoa(ur.config.AutoFlipInterval), 3, nil, func(text string) {
        if interval, err := strconv.Atoi(text); err == nil && interval > 0 {
            ur.config.AutoFlipInterval = interval
        }
    })
    
    // 显示进度
    form.AddCheckbox("显示进度", ur.config.ShowProgress, func(checked bool) {
        ur.config.ShowProgress = checked
    })
    
    // 提醒间隔
    form.AddInputField("提醒间隔(分钟)", strconv.Itoa(ur.config.RemindInterval), 3, nil, func(text string) {
        if interval, err := strconv.Atoi(text); err == nil && interval >= 0 {
            ur.config.RemindInterval = interval
        }
    })
    
    // 按钮
    form.AddButton("保存", func() {
        config.SaveConfig(ur.config)
        ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
    })
    
    form.AddButton("取消", func() {
        ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
    })
    
    // 设置ESC键处理
    form.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
        if event.Key() == tcell.KeyEsc {
            ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
            return nil
        }
        return event
    })
    
    form.SetBorder(true).SetTitle("设置")
    ur.safeSetRoot(form, form)
}

// searchTUI TUI模式搜索
func (ur *UnifiedReader) searchTUI() {
    // 创建一个输入框
    inputField := tview.NewInputField().
        SetLabel("搜索关键词: ").
        SetFieldWidth(30)
    
    form := tview.NewForm().
        AddFormItem(inputField).
        AddButton("搜索", func() {
            term := inputField.GetText()
            if term == "" {
                return
            }
            
            // 执行搜索
            results := []int{}
            for i, page := range ur.content {
                if strings.Contains(page, term) {
                    results = append(results, i)
                }
            }
            
            if len(results) == 0 {
                ur.showMessage("未找到匹配结果")
                return
            }
            
            // 显示搜索结果
            ur.showSearchResultsTUI(term, results)
        }).
        AddButton("取消", func() {
            ur.tuiApp.SetRoot(ur.tuiPages, true).SetFocus(ur.tuiTextView)
        })
    
    // 设置ESC键处理
    form.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
        if event.Key() == tcell.KeyEsc {
            ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
            return nil
        }
        return event
    })
    form.SetBorder(true).SetTitle("搜索")
    ur.tuiApp.SetRoot(form, true).SetFocus(inputField)
}

// showSearchResultsTUI 显示TUI模式搜索结果
func (ur *UnifiedReader) showSearchResultsTUI(term string, results []int) {
    list := tview.NewList().
        AddItem("返回", "返回搜索", 'b', func() {
            ur.tuiApp.SetRoot(ur.tuiPages, true).SetFocus(ur.tuiTextView)
        })
    
    // 添加搜索结果
    for i, page := range results {
        // 创建闭包内的局部变量
        pageNum := page
        list.AddItem(
            fmt.Sprintf("第 %d 页", page+1),
            fmt.Sprintf("包含: %s", term),
            rune('0'+i+1),
            func() {
                ur.currentPage = pageNum
                ur.updateTUI()
                ur.tuiApp.SetRoot(ur.tuiPages, true).SetFocus(ur.tuiTextView)
            })
    }
    
    list.SetBorder(true).SetTitle(fmt.Sprintf("搜索结果: %s (%d个)", term, len(results)))
    ur.tuiApp.SetRoot(list, true).SetFocus(list)
}

// showHelpTUITUI TUI模式显示帮助（TUI专用）
func (ur *UnifiedReader) showHelpTUITUI() {
    helpText := `
统一终端阅读器 - 帮助
====================

导航:
  空格, →, n: 下一页
  ←, p: 上一页
  Home: 第一页
  End: 最后一页
  g: 跳转到指定页面

书签:
  m: 添加书签
  l: 显示书签列表

搜索:
  /: 搜索文本

朗读:
  r: 朗读/停止朗读当前页

自动翻页:
  a: 开启/关闭自动翻页

设置:
  s: 打开设置

老板键:
  i: 一键隐藏/显示阅读器

其他:
  h: 显示帮助
  q: 退出阅读器

自动功能:
  - 自动翻页: 按配置间隔自动翻页
  - 阅读提醒: 按配置间隔提醒休息
`
    
    modal := tview.NewModal().
        SetText(helpText).
        AddButtons([]string{"确定"}).
        SetDoneFunc(func(buttonIndex int, buttonLabel string) {
            ur.tuiApp.SetRoot(ur.tuiPages, true).SetFocus(ur.tuiTextView)
        })
    
    // 设置ESC键处理
    modal.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
        if event.Key() == tcell.KeyEsc {
            ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
            return nil
        }
        return event
    })

    modal.SetBorder(true).SetTitle("帮助")
    ur.tuiApp.SetRoot(modal, false)
}

// createTitleBar 创建标题栏
func createTitleBar(filename string, currentPage, totalPages int) *tview.TextView {
    title := fmt.Sprintf("《%s》 - 第 %d/%d 页", filename, currentPage, totalPages)
    return tview.NewTextView().
        SetTextAlign(tview.AlignCenter).
        SetText(title)
}

// createStatusBar 创建状态栏
func createStatusBar(currentPage, totalPages int, autoFlip bool) *tview.TextView {
    status := fmt.Sprintf("进度: %.1f%%", float64(currentPage)/float64(totalPages)*100)
    autoStatus := ""
    if autoFlip {
        autoStatus = " [自动翻页]"
    }
    help := "空格/→/n:下一页 ←/p:上一页 g:跳转 m:书签 /:搜索 r:朗读 a:自动翻页 i:老板键 q:退出"
    return tview.NewTextView().
        SetTextAlign(tview.AlignRight).
        SetText(fmt.Sprintf("%s%s | %s", status, autoStatus, help))
}

// getIndex 获取选项在列表中的索引
func getIndex(value string, options []string) int {
    for i, option := range options {
        if option == value {
            return i
        }
    }
    return 0
}

// getTcellColor 将颜色名称映射到tcell颜色
func getTcellColor(colorName string) tcell.Color {
    switch colorName {
    case "black":
        return tcell.ColorBlack
    case "red":
        return tcell.ColorRed
    case "green":
        return tcell.ColorGreen
    case "yellow":
        return tcell.ColorYellow
    case "blue":
        return tcell.ColorBlue
    case "magenta":
        return tcell.ColorPurple // 使用 Purple 替代 Magenta
    case "cyan":
        return tcell.ColorLightBlue // 使用 LightBlue 替代 Cyan
    case "white":
        return tcell.ColorWhite
    case "gray":
        return tcell.ColorGray
    default:
        return tcell.ColorWhite
    }
}

// hideTUIReader 隐藏TUI模式阅读器
func (ur *UnifiedReader) hideTUIReader() {
    // 停止当前的TUI应用
    if ur.tuiApp != nil {
        ur.tuiApp.Stop()
    }
    
    // 创建终端模拟界面
    terminal := tview.NewTextView().
        SetDynamicColors(true).
        SetRegions(true).
        SetWordWrap(true)
    
    terminal.SetText("$ ")
    terminal.SetBorder(true).SetTitle("Terminal")
}

// showTUIReader 显示TUI模式阅读器
func (ur *UnifiedReader) showTUIReader() {    
    // 重新启动TUI模式
    ur.runTUIMode()
}

// executeShellCommandTUI 执行shell命令模拟（TUI版本）
func (ur *UnifiedReader) executeShellCommandTUI(command string) string {
    // 简单的命令模拟
    switch command {
    case "ls", "dir":
        return "file1.txt  file2.txt  documents/  downloads/"
    case "pwd":
        return "/home/user"
    case "whoami":
        return "user"
    case "date":
        return time.Now().Format("Mon Jan 2 15:04:05 MST 2006")
    case "exit", "quit":
        return "Use 'i' to return to reader"
    case "":
        return ""
    default:
        return fmt.Sprintf("bash: %s: command not found", command)
    }
}


// getPagePrimitive 获取页面组件
func (ur *UnifiedReader) getPagePrimitive(pageName string) tview.Primitive {
    if ur.tuiPages == nil {
        return nil
    }
    
    // 使用反射或其他方法来获取页面组件
    // 这里我们使用一个简单的方法：尝试获取已知的页面
    if pageName == "terminal" {
        // 返回终端界面
        return ur.createTerminalUI()
    } else if pageName == "main" {
        // 返回主界面
        return ur.createMainUI()
    }
    
    return nil
}