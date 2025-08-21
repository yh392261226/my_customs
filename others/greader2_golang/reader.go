package main

import (
	"bufio"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"time"

	"golang.org/x/term"
)

// TTSPlayer 文本转语音播放器
type TTSPlayer struct {
    cmd     *exec.Cmd
    mutex   sync.Mutex
    playing bool
    stopCh  chan struct{}
}

// Note 笔记结构
type Note struct {
	File    string `json:"file"`
	Page    int    `json:"page"`
	Content string `json:"content"`
}

// ReadingStats 阅读统计
type ReadingStats struct {
    TotalReadingTime int64 `json:"totalReadingTime"` // 总阅读时间（秒）
    PagesRead        int   `json:"pagesRead"`        // 已读页数
    BooksCompleted   int   `json:"booksCompleted"`   // 完成的书籍数量
    LastReadTime     int64 `json:"lastReadTime"`     // 最后阅读时间
    LastPage         int   `json:"lastPage"`         // 最后阅读的页码
}

// Reader 阅读器结构体
type Reader struct {
	FilePath       string
	Content        []string
	CurrentPage    int
	TotalPages     int
	Config         *Config
	Bookmarks      []Bookmark
	CurrentTTS     *TTSPlayer
	SearchTerm     string
	SearchResults  []int
	CurrentSearch  int
	IsInSetting    bool
	IsInBookmark   bool
	IsInSearch     bool
	Notes          []Note
	ReadingStats   *ReadingStats
	Book           Book          // 书籍实例
	BookTitle      string        // 书籍标题
    AutoFlipTicker   *time.Ticker  // 自动翻页计时器
	AutoFlipQuit     chan struct{} // 自动翻页退出通道
    RemindTicker     *time.Ticker  // 提醒计时器
	RemindQuit       chan struct{} // 提醒退出通道
	StartReadingTime time.Time     // 开始阅读时间
}

// NewTTSPlayer 创建新的TTS播放器
func NewTTSPlayer() *TTSPlayer {
	return &TTSPlayer{
		playing: false,
	}
}

// PlayText 播放文本
func (t *TTSPlayer) PlayText(text string, speed int) error {
    t.mutex.Lock()
    defer t.mutex.Unlock()

    // 如果正在播放，先停止
    if t.playing {
        t.stopCh <- struct{}{}
        if t.cmd != nil && t.cmd.Process != nil {
            t.cmd.Process.Kill()
        }
        t.playing = false
    }

    // 根据操作系统选择不同的TTS命令
    var cmd *exec.Cmd
    if isLinux() {
        // Linux使用espeak
        cmd = exec.Command("espeak", "-s", strconv.Itoa(speed*30), text)
    } else if isMacOS() {
        // macOS使用say
        rate := mapSpeedToRate(speed)
        cmd = exec.Command("say", "-r", rate, text)
    } else if isWindows() {
        // Windows使用PowerShell的SpeechSynthesizer
        psScript := fmt.Sprintf(
            `Add-Type -AssemblyName System.speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Rate = %d; $speak.Speak("%s");`,
            (speed-5)*2, // 将速度映射到-10到10范围
            strings.ReplaceAll(text, `"`, `\"`),
        )
        cmd = exec.Command("powershell", "-Command", psScript)
    } else {
        return fmt.Errorf("不支持的操作系统")
    }

    t.cmd = cmd
    t.playing = true
    t.stopCh = make(chan struct{}, 1)

    // 启动TTS进程
    go func() {
        err := cmd.Run()
        
        t.mutex.Lock()
        defer t.mutex.Unlock()
        
        // 检查是否是被主动停止的
        select {
        case <-t.stopCh:
            // 是被主动停止的，不更新状态
        default:
            t.playing = false
        }
        
        if err != nil && err.Error() != "signal: killed" {
            fmt.Printf("TTS错误: %v\n", err)
        }
    }()

    return nil
}

// Stop 停止播放
func (t *TTSPlayer) Stop() {
    t.mutex.Lock()
    defer t.mutex.Unlock()

    if t.playing {
        t.stopCh <- struct{}{}
        if t.cmd != nil && t.cmd.Process != nil {
            t.cmd.Process.Kill()
        }
        t.playing = false
    }
}

// IsPlaying 检查是否正在播放
func (t *TTSPlayer) IsPlaying() bool {
    t.mutex.Lock()
    defer t.mutex.Unlock()
    return t.playing
}

// 辅助函数：检测操作系统
func isLinux() bool {
	return strings.Contains(strings.ToLower(os.Getenv("OS")), "linux") ||
		strings.Contains(strings.ToLower(runtime.GOOS), "linux")
}

func isMacOS() bool {
	return strings.Contains(strings.ToLower(os.Getenv("OS")), "darwin") ||
		strings.Contains(strings.ToLower(runtime.GOOS), "darwin")
}

func isWindows() bool {
	return strings.Contains(strings.ToLower(os.Getenv("OS")), "windows") ||
		strings.Contains(strings.ToLower(runtime.GOOS), "windows")
}

// 将速度值映射到macOS的语速范围
func mapSpeedToRate(speed int) string {
	// 将1-10的速度映射到150-300的语速范围
	rate := 150 + (speed-1)*15
	return strconv.Itoa(rate)
}

// NewReader 创建新的阅读器实例
func NewReader(filePath string) (*Reader, error) {
	// 加载配置
	config := loadConfig()

	// 打开书籍文件
	book, err := OpenBook(filePath)
	if err != nil {
		return nil, err
	}

	// 获取书籍内容
	content, err := book.GetContent()
	if err != nil {
		book.Close()
		return nil, err
	}

	// 获取书籍元数据
	metadata := book.GetMetadata()

	reader := &Reader{
		FilePath:    filePath,
		Content:     content,
		CurrentPage: 0,
		TotalPages:  len(content),
		Config:      config,
		Book:        book, // 保存书籍实例
		BookTitle:   metadata.Title, // 保存书籍标题
        StartReadingTime: time.Now(), // 记录开始阅读时间
	}
    // 启动提醒计时器
    if config.RemindInterval > 0 {
        reader.startRemindTimer()
    }

	// 加载书签
	reader.Bookmarks = loadBookmarksForFile(filePath)

	// 加载笔记
	reader.Notes = loadNotes(filePath)

	// 加载阅读统计
	reader.ReadingStats = loadReadingStats(filePath)
	
	// 如果存在阅读统计，恢复上次阅读位置
	if reader.ReadingStats != nil && reader.ReadingStats.LastPage > 0 {
		// 确保页码在有效范围内
		if reader.ReadingStats.LastPage < reader.TotalPages {
			reader.CurrentPage = reader.ReadingStats.LastPage
		} else {
			reader.CurrentPage = reader.TotalPages - 1
		}
	}

	return reader, nil
}

// Run 启动阅读器主循环
func (r *Reader) Run() error {
	// 初始化TTS
	r.CurrentTTS = NewTTSPlayer()

	// 初始化阅读统计
	if r.ReadingStats == nil {
		r.ReadingStats = &ReadingStats{}
	}

	// 记录开始阅读时间
	startTime := time.Now().Unix()

	// 检查标准输入是否是终端设备
	isTerminal := term.IsTerminal(int(os.Stdin.Fd()))
	
	// 只有在终端设备上才初始化UI
	if isTerminal {
		if err := initUI(); err != nil {
			return err
		}
		defer cleanupUI()
	}

    // 确保书籍被关闭
	defer r.Book.Close()

    // 确保自动翻页被停止
    defer r.stopAutoFlip()

    // 如果配置启用了自动翻页，启动它
    if r.Config.AutoFlipEnabled && r.Config.AutoFlipInterval > 0 {
        r.startAutoFlip()
    }

	// 只有在终端设备上才渲染页面
	if isTerminal {
		r.RenderPage()
	}

	// 主事件循环
	for {
		// 处理输入
		key, err := getInput()
		if err != nil {
			return err
		}

		// 如果在隐藏状态，只响应i键
		if isWindowHidden {
			if key == "i" {
				r.HideWindow()
				// 恢复后重新渲染页面
				r.RenderPage()
			}
			// 忽略其他所有按键
			continue
		}

		// 处理按键
		switch key {
		case "up", "left", " ":
			r.PreviousPage()
		case "down", "right":
			r.NextPage()
		case "s":
			if isTerminal {
				r.ShowSettings()
			}
		case "h":
			if isTerminal {
				r.ShowHelp()
			}
		case "f":
			if isTerminal {
				r.ShowBookmarks()
			}
		case "b":
			if isTerminal {
				r.ToggleBookmark()
			}
		case "/":
			if isTerminal {
				r.StartSearch()
			}
		case "r":
			r.ToggleReadAloud()
		case "q":
			// 更新阅读统计
			r.updateReadingStats(startTime)
			return nil
		case "i":  // 隐藏/显示窗口
			if isTerminal {
				r.HideWindow()
			}
		case "g":
			if isTerminal {
				r.GoToBookmark()
			}
		case "l":
			if isTerminal {
				r.GoToPage()
			}
		case "n":
			r.NextSearchResult()
		case "p":
			r.PreviousSearchResult()
		case "t": // 添加笔记
			if isTerminal {
				r.AddNote()
			}
		case "v": // 查看笔记
			if isTerminal {
				r.ShowNotes()
			}
		case "e": // 导出数据
			if isTerminal {
				r.ExportData()
			}
		case "x": // 查看阅读统计
			if isTerminal {
				r.ShowReadingStats()
			}
        case "a": // 自动翻页
            if r.Config.AutoFlipEnabled {
                r.stopAutoFlip()
            } else {
                r.startAutoFlip()
            }
            // 立即重新渲染以显示状态变化
            if isTerminal {
				r.RenderPage()
			}
		case "esc":
			if r.IsInSetting || r.IsInBookmark || r.IsInSearch {
                r.IsInSetting = false
                r.IsInBookmark = false
                r.IsInSearch = false
            } else {
                // 更新阅读统计
                r.updateReadingStats(startTime)
                // 停止自动翻页
                r.stopAutoFlip()
                return nil
            }
		}

		// 只有在终端设备上才重新渲染页面
		if isTerminal {
			r.RenderPage()
		}
	}
}

// RenderPage 渲染当前页
func (r *Reader) RenderPage() {
    if isWindowHidden {
        return
    }

    clearScreen()

    // 绘制边框
    if r.Config.BorderStyle != "none" {
        drawBorder(r.Config.BorderStyle, r.Config.Width, r.Config.Height)
    }

    // 计算内容区域
    contentWidth := r.Config.Width - 2*r.Config.Margin - 2*r.Config.Padding
    contentHeight := r.Config.Height - 2*r.Config.Margin - 2*r.Config.Padding - 4 // 增加底部信息行

    // 显示标题
    var title string
    if r.BookTitle == "" {
        title = fmt.Sprintf("《%s》", getFileName(r.FilePath))
    } else {
        title = fmt.Sprintf("《%s》", r.BookTitle)
    }
    displayText(1+r.Config.Margin, 0+r.Config.Margin, title, r.Config.FontColor, r.Config.BgColor)

    // 显示内容
    if r.CurrentPage < len(r.Content) {
        lines := wrapText(r.Content[r.CurrentPage], contentWidth)
        for i, line := range lines {
            if i >= contentHeight {
                break
            }
            yPos := 1 + i + r.Config.Margin + r.Config.Padding
            displayText(1+r.Config.Margin+r.Config.Padding, yPos, line, r.Config.FontColor, r.Config.BgColor)
        }
    }

    // 显示进度
	var progressStr string
	if r.Config.ShowProgress {
		// 计算百分比
		percentage := float64(r.CurrentPage+1) / float64(r.TotalPages) * 100
		progressStr = fmt.Sprintf("进度: %d/%d (%.1f%%)",
			r.CurrentPage+1, r.TotalPages, percentage)
		
		// 显示进度条
		displayProgressBar(1+r.Config.Margin, r.Config.Height-4-r.Config.Margin,
			r.Config.Width-2*r.Config.Margin, r.CurrentPage+1, r.TotalPages,
			r.Config.FontColor, r.Config.BgColor)
	}

	// 绘制底部状态栏
	shortcuts := getShortcutHint()
	drawBottomStatusBar(r.Config.BorderStyle, r.Config.Width, r.Config.Height, 
		progressStr, shortcuts, r.Config.FontColor, r.Config.BgColor)

    // 显示搜索高亮
    if r.SearchTerm != "" {
        r.highlightSearchTerms()
    }

    // 显示当前模式提示
    modeLine := ""
    if r.IsInSetting {
        modeLine = "设置模式 - 按ESC退出"
    } else if r.IsInBookmark {
        modeLine = "书签模式 - 按ESC退出"
    } else if r.IsInSearch {
        modeLine = fmt.Sprintf("搜索模式: %s (%d/%d) - 按ESC退出", 
            r.SearchTerm, r.CurrentSearch+1, len(r.SearchResults))
    }
    
    if modeLine != "" {
        displayText(1+r.Config.Margin, r.Config.Height-4-r.Config.Margin, modeLine, r.Config.FontColor, r.Config.BgColor)
    }

    // 显示朗读状态
    if r.CurrentTTS.IsPlaying() {
        statusText := "朗读中..."
        displayText(r.Config.Width-len(statusText)-r.Config.Margin-1, 0, statusText, r.Config.FontColor, r.Config.BgColor)
    }

    // 显示自动翻页状态
    if r.Config.AutoFlipEnabled {
        statusText := fmt.Sprintf("自动翻页中(%ds)", r.Config.AutoFlipInterval)
        // 确保状态文本不会超出屏幕
        if len(statusText) > r.Config.Width-2 {
            statusText = statusText[:r.Config.Width-2]
        }
        displayText(r.Config.Width-len(statusText)-r.Config.Margin-1, 1, statusText, r.Config.FontColor, r.Config.BgColor)
    }
}

// PreviousPage 上一页
func (r *Reader) PreviousPage() {
	if r.CurrentPage > 0 {
		r.CurrentPage--
	}
}

// NextPage 下一页
func (r *Reader) NextPage() {
	if r.CurrentPage < r.TotalPages-1 {
		r.CurrentPage++
	}
}

// ShowSettings 显示设置界面
func (r *Reader) ShowSettings() {
    r.IsInSetting = true
    
    // 设置选项
    options := []string{
        "宽度: " + strconv.Itoa(r.Config.Width),
        "高度: " + strconv.Itoa(r.Config.Height),
        "字体大小: " + strconv.Itoa(r.Config.FontSize),
        "字体颜色: " + r.Config.FontColor,
        "背景颜色: " + r.Config.BgColor,
        "边框样式: " + r.Config.BorderStyle,
        "显示进度条: " + strconv.FormatBool(r.Config.ShowProgress),
        "边距: " + strconv.Itoa(r.Config.Margin),
        "内边距: " + strconv.Itoa(r.Config.Padding),
        "行间距: " + strconv.Itoa(r.Config.LineSpacing),
        "朗读速度: " + strconv.Itoa(r.Config.TTSSpeed),
        "自动朗读: " + strconv.FormatBool(r.Config.AutoReadAloud),
        "自动翻页间隔: " + strconv.Itoa(r.Config.AutoFlipInterval) + "秒",
        "自动翻页: " + strconv.FormatBool(r.Config.AutoFlipEnabled),
        "阅读提醒间隔: " + strconv.Itoa(r.Config.RemindInterval) + "分钟",
        "保存并退出",
    }
    
    selected := 0
    for r.IsInSetting {
        clearScreen()
        
        // 计算居中位置
        _, height, _ := getTerminalSize()
        startY := (height - len(options) - 3) / 2
        
        // 显示标题
        displayText(2, startY, "设置 - 使用上下键选择，回车键修改，ESC退出", r.Config.FontColor, r.Config.BgColor)
        displayText(2, startY+1, "========================================", r.Config.FontColor, r.Config.BgColor)
        
        // 显示选项
        for i, option := range options {
            y := startY + 2 + i
            if i == selected {
                displayText(2, y, "> "+option, r.Config.FontColor, r.Config.BgColor)
            } else {
                displayText(2, y, "  "+option, r.Config.FontColor, r.Config.BgColor)
            }
        }
        
        key, err := getInput()
        if err != nil {
            break
        }
        
        switch key {
        case "up":
            if selected > 0 {
                selected--
            }
        case "down":
            if selected < len(options)-1 {
                selected++
            }
        case "enter":
            r.modifySetting(selected)
            // 更新选项显示
            options = []string{
                "宽度: " + strconv.Itoa(r.Config.Width),
                "高度: " + strconv.Itoa(r.Config.Height),
                "字体大小: " + strconv.Itoa(r.Config.FontSize),
                "字体颜色: " + r.Config.FontColor,
                "背景颜色: " + r.Config.BgColor,
                "边框样式: " + r.Config.BorderStyle,
                "显示进度条: " + strconv.FormatBool(r.Config.ShowProgress),
                "边距: " + strconv.Itoa(r.Config.Margin),
                "内边距: " + strconv.Itoa(r.Config.Padding),
                "行间距: " + strconv.Itoa(r.Config.LineSpacing),
                "朗读速度: " + strconv.Itoa(r.Config.TTSSpeed),
                "自动朗读: " + strconv.FormatBool(r.Config.AutoReadAloud),
                "自动翻页间隔: " + strconv.Itoa(r.Config.AutoFlipInterval) + "秒",
                "自动翻页: " + strconv.FormatBool(r.Config.AutoFlipEnabled),
                "阅读提醒间隔: " + strconv.Itoa(r.Config.RemindInterval) + "分钟",
                "保存并退出",
            }
        case "esc":
            r.IsInSetting = false
            // 保存配置
            saveConfig(r.Config)
            return
        }
    }
}

// modifySetting 修改设置项
func (r *Reader) modifySetting(selected int) {
	switch selected {
	case 0: // 宽度
		input := showInputPrompt("请输入宽度: ")
		if width, err := strconv.Atoi(input); err == nil && width > 0 {
			r.Config.Width = width
		}
	case 1: // 高度
		input := showInputPrompt("请输入高度: ")
		if height, err := strconv.Atoi(input); err == nil && height > 0 {
			r.Config.Height = height
		}
	case 2: // 字体大小
		input := showInputPrompt("请输入字体大小: ")
		if size, err := strconv.Atoi(input); err == nil && size > 0 {
			r.Config.FontSize = size
		}
	case 3: // 字体颜色
		colors := []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"}
		currentIndex := 0
		for i, color := range colors {
			if color == r.Config.FontColor {
				currentIndex = i
				break
			}
		}
		nextIndex := (currentIndex + 1) % len(colors)
		r.Config.FontColor = colors[nextIndex]
	case 4: // 背景颜色
		colors := []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "transparent"}
		currentIndex := 0
		for i, color := range colors {
			if color == r.Config.BgColor {
				currentIndex = i
				break
			}
		}
		nextIndex := (currentIndex + 1) % len(colors)
		r.Config.BgColor = colors[nextIndex]
	case 5: // 边框样式
		styles := []string{"round", "bold", "double", "thin", "none"}
		currentIndex := 0
		for i, style := range styles {
			if style == r.Config.BorderStyle {
				currentIndex = i
				break
			}
		}
		nextIndex := (currentIndex + 1) % len(styles)
		r.Config.BorderStyle = styles[nextIndex]
	case 6: // 显示进度条
		r.Config.ShowProgress = !r.Config.ShowProgress
	case 7: // 边距
		input := showInputPrompt("请输入边距: ")
		if margin, err := strconv.Atoi(input); err == nil && margin >= 0 {
			r.Config.Margin = margin
		}
	case 8: // 内边距
		input := showInputPrompt("请输入内边距: ")
		if padding, err := strconv.Atoi(input); err == nil && padding >= 0 {
			r.Config.Padding = padding
		}
	case 9: // 行间距
		input := showInputPrompt("请输入行间距: ")
		if spacing, err := strconv.Atoi(input); err == nil && spacing >= 0 {
			r.Config.LineSpacing = spacing
		}
	case 10: // 朗读速度
		input := showInputPrompt("请输入朗读速度 (1-10): ")
		if speed, err := strconv.Atoi(input); err == nil && speed >= 1 && speed <= 10 {
			r.Config.TTSSpeed = speed
		}
	case 11: // 自动朗读
		r.Config.AutoReadAloud = !r.Config.AutoReadAloud
	case 12: // 自动翻页间隔
        input := showInputPrompt("请输入自动翻页间隔(秒): ")
        if interval, err := strconv.Atoi(input); err == nil && interval > 0 {
            r.Config.AutoFlipInterval = interval
        } else {
            // 如果输入无效，设置为默认值
            r.Config.AutoFlipInterval = 5
        }
        // 保存配置
        saveConfig(r.Config)
    case 13: // 自动翻页
        r.Config.AutoFlipEnabled = !r.Config.AutoFlipEnabled
        // 如果启用自动翻页，确保有合理的间隔
        if r.Config.AutoFlipEnabled && r.Config.AutoFlipInterval <= 0 {
            r.Config.AutoFlipInterval = 5
        }
        // 保存配置
        saveConfig(r.Config)
        // 根据设置启动或停止自动翻页
        if r.Config.AutoFlipEnabled {
            r.startAutoFlip()
        } else {
            r.stopAutoFlip()
        }
    case 14: // 阅读提醒间隔
        input := showInputPrompt("请输入阅读提醒间隔(分钟，0表示不提醒): ")
        if interval, err := strconv.Atoi(input); err == nil && interval >= 0 {
            r.Config.RemindInterval = interval
            // 根据设置启动或停止提醒计时器
            if r.Config.RemindInterval > 0 {
                r.startRemindTimer()
            } else {
                r.stopRemindTimer()
            }
        }
    case 15: // 保存并退出
		saveConfig(r.Config)
		r.IsInSetting = false
	}
}

func (r *Reader) ShowHelp() {
    clearScreen()
    
    helpLines := []string{
        "快捷键帮助:",
        "========================================",
        "上/左/空格: 上一页",
        "下/右: 下一页",
        "s: 打开设置",
        "h: 打开帮助",
        "f: 打开书签",
        "b: 收藏/取消收藏",
        "/: 搜索",
        "r: 朗读/取消朗读",
        "q: 退出",
        "i: 隐藏/显示窗口",
        "g: 跳转到书签",
        "l: 跳转到页码",
        "n: 下一个搜索结果",
        "p: 上一个搜索结果",
        "t: 添加笔记",
        "v: 查看笔记",
        "e: 导出数据",
        "x: 查看阅读统计",
        "a: 自动翻页/取消自动翻页", // 新增自动翻页快捷键
        "ESC: 返回",
        "",
        "支持格式: TXT, EPUB, PDF, MOBI",
        "",
        "按任意键继续...",
    }
    
    // 计算居中位置
    _, height, _ := getTerminalSize()
    startY := (height - len(helpLines)) / 2
    
    for i, line := range helpLines {
        x := 2
        y := startY + i
        if y >= 0 && y < height {
            displayText(x, y, line, r.Config.FontColor, r.Config.BgColor)
        }
    }
    
    // 等待按键
    getInput()
}

// ShowBookmarks 显示书签
func (r *Reader) ShowBookmarks() {
    r.IsInBookmark = true
    
    if len(r.Bookmarks) == 0 {
        clearScreen()
        displayText(2, 2, "没有书签", r.Config.FontColor, r.Config.BgColor)
        displayText(2, 4, "按任意键继续...", r.Config.FontColor, r.Config.BgColor)
        getInput()
        r.IsInBookmark = false
        return
    }

    selected := 0
    for r.IsInBookmark {
        clearScreen()
        
        // 获取终端大小
        width, height, _ := getTerminalSize()
        
        // 显示标题
        title := "书签列表 - 使用上下键选择，回车键跳转，d键删除，ESC退出"
        displayText((width-len(title))/2, 2, title, r.Config.FontColor, r.Config.BgColor)
        
        // 显示分隔线
        separator := strings.Repeat("=", width-4)
        displayText(2, 3, separator, r.Config.FontColor, r.Config.BgColor)
        
        // 计算可显示的书签数量
        maxItems := height - 6
        startIdx := 0
        if selected >= maxItems {
            startIdx = selected - maxItems + 1
        }
        
        endIdx := startIdx + maxItems
        if endIdx > len(r.Bookmarks) {
            endIdx = len(r.Bookmarks)
        }
        
        // 显示书签列表
        for i := startIdx; i < endIdx; i++ {
            bookmark := r.Bookmarks[i]
            label := bookmark.Label
            if label == "" {
                label = fmt.Sprintf("第%d页", bookmark.Page+1)
            }
            
            y := 5 + (i - startIdx)
            if i == selected {
                displayText(4, y, "> "+label, r.Config.FontColor, r.Config.BgColor)
            } else {
                displayText(4, y, "  "+label, r.Config.FontColor, r.Config.BgColor)
            }
            
            // 显示文件名
            fileName := filepath.Base(bookmark.File)
            if len(fileName) > 20 {
                fileName = fileName[:17] + "..."
            }
            displayText(width-24, y, fileName, r.Config.FontColor, r.Config.BgColor)
        }
        
        // 显示滚动提示
        if startIdx > 0 {
            displayText(2, 5, "↑ 更多...", r.Config.FontColor, r.Config.BgColor)
        }
        if endIdx < len(r.Bookmarks) {
            displayText(2, height-2, "↓ 更多...", r.Config.FontColor, r.Config.BgColor)
        }

        key, err := getInput()
        if err != nil {
            break
        }

        switch key {
        case "up":
            if selected > 0 {
                selected--
            }
        case "down":
            if selected < len(r.Bookmarks)-1 {
                selected++
            }
        case "enter":
            r.CurrentPage = r.Bookmarks[selected].Page
            r.IsInBookmark = false
            return
        case "d":
            // 删除书签
            r.Bookmarks = append(r.Bookmarks[:selected], r.Bookmarks[selected+1:]...)
            saveBookmarks(r.FilePath, r.Bookmarks)
            if len(r.Bookmarks) == 0 {
                r.IsInBookmark = false
                return
            }
            if selected >= len(r.Bookmarks) {
                selected = len(r.Bookmarks) - 1
            }
        case "esc":
            r.IsInBookmark = false
            return
        }
    }
}


// ToggleBookmark 切换书签状态
func (r *Reader) ToggleBookmark() {
	// 检查当前页是否已经有书签
	for i, bookmark := range r.Bookmarks {
		if bookmark.Page == r.CurrentPage {
			// 删除书签
			r.Bookmarks = append(r.Bookmarks[:i], r.Bookmarks[i+1:]...)
			saveBookmarks(r.FilePath, r.Bookmarks)
			return
		}
	}

	// 添加新书签
	label := showInputPrompt("请输入书签名称 (直接回车使用默认名称): ")
	if label == "" {
		label = fmt.Sprintf("第%d页", r.CurrentPage+1)
	}

	newBookmark := Bookmark{
		File:  r.FilePath,
		Page:  r.CurrentPage,
		Label: label,
	}

	r.Bookmarks = append(r.Bookmarks, newBookmark)
	saveBookmarks(r.FilePath, r.Bookmarks)
}

// StartSearch 开始搜索
func (r *Reader) StartSearch() {
    r.IsInSearch = true
    
    // 恢复终端状态以显示输入提示
    if oldState != nil {
        term.Restore(int(os.Stdin.Fd()), oldState)
    }
    
    defer func() {
        // 恢复原始模式
        if oldState != nil {
            term.MakeRaw(int(os.Stdin.Fd()))
        }
    }()
    
    clearScreen()
    fmt.Print("请输入搜索关键词: ")
    
    reader := bufio.NewReader(os.Stdin)
    term, _ := reader.ReadString('\n')
    term = strings.TrimSpace(term)
    
    if term == "" {
        r.IsInSearch = false
        return
    }

    r.SearchTerm = term
    r.SearchResults = []int{}

    // 在所有页面中搜索关键词
    for i, page := range r.Content {
        if strings.Contains(page, term) {
            r.SearchResults = append(r.SearchResults, i)
        }
    }

    if len(r.SearchResults) == 0 {
        clearScreen()
        fmt.Println("未找到匹配结果")
        fmt.Println("\n按任意键继续...")
        getInput()
        r.IsInSearch = false
        r.SearchTerm = ""
        return
    }

    r.CurrentSearch = 0
    r.CurrentPage = r.SearchResults[r.CurrentSearch]
}

// ToggleReadAloud 切换朗读状态
func (r *Reader) ToggleReadAloud() {
    if r.CurrentTTS.IsPlaying() {
        r.CurrentTTS.Stop()
    } else {
        // 朗读当前页内容
        if r.CurrentPage < len(r.Content) {
            text := r.Content[r.CurrentPage]
            // 限制文本长度，避免TTS命令过长
            if len(text) > 1000 {
                text = text[:1000] + "..."
            }
            r.CurrentTTS.PlayText(text, r.Config.TTSSpeed)
        }
    }
}

// HideWindow 隐藏/显示窗口
func (r *Reader) HideWindow() {
    if isWindowHidden {
        showWindow()
        isWindowHidden = false
    } else {
        hideWindow()
        isWindowHidden = true
    }
}

// GoToBookmark 跳转到书签
func (r *Reader) GoToBookmark() {
	if len(r.Bookmarks) == 0 {
		fmt.Println("没有书签")
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}

	// 显示书签列表并跳转
	r.ShowBookmarks()
}

// GoToPage 跳转到指定页码
func (r *Reader) GoToPage() {
	input := showInputPrompt("请输入页码: ")
	if page, err := strconv.Atoi(input); err == nil && page > 0 && page <= r.TotalPages {
		r.CurrentPage = page - 1
	}
}

// NextSearchResult 下一个搜索结果
func (r *Reader) NextSearchResult() {
	if len(r.SearchResults) == 0 {
		return
	}

	r.CurrentSearch = (r.CurrentSearch + 1) % len(r.SearchResults)
	r.CurrentPage = r.SearchResults[r.CurrentSearch]
}

// PreviousSearchResult 上一个搜索结果
func (r *Reader) PreviousSearchResult() {
	if len(r.SearchResults) == 0 {
		return
	}

	r.CurrentSearch = (r.CurrentSearch - 1 + len(r.SearchResults)) % len(r.SearchResults)
	r.CurrentPage = r.SearchResults[r.CurrentSearch]
}

// ClearSearch 清除搜索
func (r *Reader) ClearSearch() {
	r.SearchTerm = ""
	r.SearchResults = nil
	r.CurrentSearch = 0
}

// AddNote 添加笔记
func (r *Reader) AddNote() {
    if r.CurrentPage >= len(r.Content) {
        return
    }

    // 恢复终端状态以显示输入提示
    if oldState != nil {
        term.Restore(int(os.Stdin.Fd()), oldState)
    }
    
    defer func() {
        // 恢复原始模式
        if oldState != nil {
            term.MakeRaw(int(os.Stdin.Fd()))
        }
    }()
    
    clearScreen()
    fmt.Print("请输入笔记内容: ")
    
    reader := bufio.NewReader(os.Stdin)
    noteContent, _ := reader.ReadString('\n')
    noteContent = strings.TrimSpace(noteContent)
    
    if noteContent == "" {
        return
    }

    // 创建新笔记
    newNote := Note{
        File:    r.FilePath,
        Page:    r.CurrentPage,
        Content: noteContent,
    }

    // 添加到笔记列表
    r.Notes = append(r.Notes, newNote)

    // 保存笔记
    saveNotes(r.FilePath, r.Notes)

    // 显示保存成功消息
    clearScreen()
    fmt.Println("笔记已保存")
    time.Sleep(1 * time.Second) // 显示消息1秒
}

// ShowNotes 显示笔记列表
func (r *Reader) ShowNotes() {
    if len(r.Notes) == 0 {
        clearScreen()
        fmt.Println("没有笔记")
        fmt.Println("\n按任意键继续...")
        getInput()
        return
    }

    selected := 0
    for {
        clearScreen()
        
        // 获取终端大小
        width, height, _ := getTerminalSize()
        
        // 显示标题
        title := "笔记列表 - 使用上下键选择，回车键查看，d键删除，ESC退出"
        displayText((width-len(title))/2, 2, title, r.Config.FontColor, r.Config.BgColor)
        displayText(2, 3, strings.Repeat("=", width-4), r.Config.FontColor, r.Config.BgColor)
        
        // 计算可显示的笔记数量
        maxItems := height - 6
        startIdx := 0
        if selected >= maxItems {
            startIdx = selected - maxItems + 1
        }
        
        endIdx := startIdx + maxItems
        if endIdx > len(r.Notes) {
            endIdx = len(r.Notes)
        }
        
        // 显示笔记列表
        for i := startIdx; i < endIdx; i++ {
            note := r.Notes[i]
            // 显示笔记预览
            preview := note.Content
            if len(preview) > 50 {
                preview = preview[:50] + "..."
            }
            
            line := fmt.Sprintf("第%d页: %s", note.Page+1, preview)
            y := 5 + (i - startIdx)
            
            if i == selected {
                displayText(4, y, "> "+line, r.Config.FontColor, r.Config.BgColor)
            } else {
                displayText(4, y, "  "+line, r.Config.FontColor, r.Config.BgColor)
            }
        }
        
        // 显示滚动提示
        if startIdx > 0 {
            displayText(2, 5, "↑ 更多...", r.Config.FontColor, r.Config.BgColor)
        }
        if endIdx < len(r.Notes) {
            displayText(2, height-2, "↓ 更多...", r.Config.FontColor, r.Config.BgColor)
        }

        key, err := getInput()
        if err != nil {
            break
        }

        switch key {
        case "up":
            if selected > 0 {
                selected--
            }
        case "down":
            if selected < len(r.Notes)-1 {
                selected++
            }
        case "enter":
            // 查看笔记详情
            clearScreen()
            title := fmt.Sprintf("笔记详情 (第%d页):", r.Notes[selected].Page+1)
            displayText((width-len(title))/2, 2, title, r.Config.FontColor, r.Config.BgColor)
            displayText(2, 3, strings.Repeat("=", width-4), r.Config.FontColor, r.Config.BgColor)
            
            // 显示笔记内容，自动换行
            lines := wrapText(r.Notes[selected].Content, width-4)
            for i, line := range lines {
                if i+5 >= height {
                    break
                }
                displayText(2, 5+i, line, r.Config.FontColor, r.Config.BgColor)
            }
            
            displayText(2, height-2, "按任意键返回...", r.Config.FontColor, r.Config.BgColor)
            getInput()
        case "d":
            // 删除笔记
            r.Notes = append(r.Notes[:selected], r.Notes[selected+1:]...)
            saveNotes(r.FilePath, r.Notes)
            if len(r.Notes) == 0 {
                return
            }
            if selected >= len(r.Notes) {
                selected = len(r.Notes) - 1
            }
        case "esc":
            return
        }
    }
}

// ShowReadingStats 显示阅读统计
func (r *Reader) ShowReadingStats() {
    clearScreen()
    
    // 获取终端大小
    width, height, _ := getTerminalSize()
    
    // 显示标题
    title := "阅读统计:"
    displayText((width-len(title))/2, 2, title, r.Config.FontColor, r.Config.BgColor)
    displayText(2, 3, strings.Repeat("=", width-4), r.Config.FontColor, r.Config.BgColor)
    
    // 计算阅读时间
    hours := r.ReadingStats.TotalReadingTime / 3600
    minutes := (r.ReadingStats.TotalReadingTime % 3600) / 60
    seconds := r.ReadingStats.TotalReadingTime % 60

    // 显示统计信息
    stats := []string{
        fmt.Sprintf("总阅读时间: %d小时%d分钟%d秒", hours, minutes, seconds),
        fmt.Sprintf("已读页数: %d", r.ReadingStats.PagesRead),
        fmt.Sprintf("已完成书籍: %d", r.ReadingStats.BooksCompleted),
    }
    
    // 显示最后阅读时间
    if r.ReadingStats.LastReadTime > 0 {
        lastRead := time.Unix(r.ReadingStats.LastReadTime, 0)
        stats = append(stats, fmt.Sprintf("最后阅读时间: %s", lastRead.Format("2006-01-02 15:04:05")))
    }
    
    // 显示统计信息
    for i, stat := range stats {
        if i+5 < height {
            displayText(2, 5+i, stat, r.Config.FontColor, r.Config.BgColor)
        }
    }
    
    displayText(2, height-2, "按任意键继续...", r.Config.FontColor, r.Config.BgColor)
    getInput()
}

// ExportData 导出功能
func (r *Reader) ExportData() {
    selected := 0
    options := []string{
        "导出书签",
        "导出笔记",
        "导出阅读统计",
        "返回",
    }
    
    for {
        clearScreen()
        
        // 获取终端大小
        width, height, _ := getTerminalSize()
        
        // 显示标题
        title := "导出数据:"
        displayText((width-len(title))/2, 2, title, r.Config.FontColor, r.Config.BgColor)
        displayText(2, 3, strings.Repeat("=", width-4), r.Config.FontColor, r.Config.BgColor)
        
        // 计算居中位置
        startY := (height - len(options) - 3) / 2
        
        // 显示选项
        for i, option := range options {
            y := startY + i
            if i == selected {
                displayText((width-len(option))/2, y, "> "+option, r.Config.FontColor, r.Config.BgColor)
            } else {
                displayText((width-len(option))/2, y, "  "+option, r.Config.FontColor, r.Config.BgColor)
            }
        }
        
        key, err := getInput()
        if err != nil {
            break
        }
        
        switch key {
        case "up":
            if selected > 0 {
                selected--
            }
        case "down":
            if selected < len(options)-1 {
                selected++
            }
        case "enter":
            switch selected {
            case 0:
                r.exportBookmarks()
            case 1:
                r.exportNotes()
            case 2:
                r.exportStats()
            case 3:
                return
            }
        case "esc":
            return
        }
    }
}

// exportBookmarks 导出书签
func (r *Reader) exportBookmarks() {
	if len(r.Bookmarks) == 0 {
		fmt.Println("没有书签可导出")
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}

	// 获取导出路径
	exportPath := showInputPrompt("请输入导出路径 (默认: ./bookmarks.csv): ")
	if exportPath == "" {
		exportPath = "./bookmarks.csv"
	}

	// 创建CSV文件
	file, err := os.Create(exportPath)
	if err != nil {
		fmt.Printf("创建文件失败: %v\n", err)
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}
	defer file.Close()

	// 创建CSV writer
	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	writer.Write([]string{"文件", "页码", "标签"})

	// 写入书签数据
	for _, bookmark := range r.Bookmarks {
		writer.Write([]string{
			bookmark.File,
			strconv.Itoa(bookmark.Page + 1),
			bookmark.Label,
		})
	}

	fmt.Printf("书签已导出到: %s\n", exportPath)
	fmt.Println("\n按任意键继续...")
	getInput()
}

// exportNotes 导出笔记
func (r *Reader) exportNotes() {
	if len(r.Notes) == 0 {
		fmt.Println("没有笔记可导出")
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}

	// 获取导出路径
	exportPath := showInputPrompt("请输入导出路径 (默认: ./notes.csv): ")
	if exportPath == "" {
		exportPath = "./notes.csv"
	}

	// 创建CSV文件
	file, err := os.Create(exportPath)
	if err != nil {
		fmt.Printf("创建文件失败: %v\n", err)
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}
	defer file.Close()

	// 创建CSV writer
	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	writer.Write([]string{"文件", "页码", "内容"})

	// 写入笔记数据
	for _, note := range r.Notes {
		writer.Write([]string{
			note.File,
			strconv.Itoa(note.Page + 1),
			note.Content,
		})
	}

	fmt.Printf("笔记已导出到: %s\n", exportPath)
	fmt.Println("\n按任意键继续...")
	getInput()
}

// exportStats 导出阅读统计
func (r *Reader) exportStats() {
	// 获取导出路径
	exportPath := showInputPrompt("请输入导出路径 (默认: ./stats.csv): ")
	if exportPath == "" {
		exportPath = "./stats.csv"
	}

	// 创建CSV文件
	file, err := os.Create(exportPath)
	if err != nil {
		fmt.Printf("创建文件失败: %v\n", err)
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}
	defer file.Close()

	// 创建CSV writer
	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	writer.Write([]string{"文件", "总阅读时间(秒)", "已读页数", "已完成书籍", "最后阅读时间"})

	// 计算阅读时间
	hours := r.ReadingStats.TotalReadingTime / 3600
	minutes := (r.ReadingStats.TotalReadingTime % 3600) / 60
	seconds := r.ReadingStats.TotalReadingTime % 60
	readingTimeStr := fmt.Sprintf("%d小时%d分钟%d秒", hours, minutes, seconds)

	// 格式化最后阅读时间
	lastReadTime := ""
	if r.ReadingStats.LastReadTime > 0 {
		lastRead := time.Unix(r.ReadingStats.LastReadTime, 0)
		lastReadTime = lastRead.Format("2006-01-02 15:04:05")
	}

	// 写入统计数据
	writer.Write([]string{
		r.FilePath,
		readingTimeStr,
		strconv.Itoa(r.ReadingStats.PagesRead),
		strconv.Itoa(r.ReadingStats.BooksCompleted),
		lastReadTime,
	})

	fmt.Printf("统计已导出到: %s\n", exportPath)
	fmt.Println("\n按任意键继续...")
	getInput()
}

// updateReadingStats 更新阅读统计
func (r *Reader) updateReadingStats(startTime int64) {
    currentTime := time.Now().Unix()
    r.ReadingStats.TotalReadingTime += currentTime - startTime
    r.ReadingStats.PagesRead = r.CurrentPage // 更新已读页数为当前页
    r.ReadingStats.LastReadTime = currentTime
    r.ReadingStats.LastPage = r.CurrentPage // 记录最后阅读位置

    // 如果读完了整本书，增加已完成书籍计数
    if r.CurrentPage >= r.TotalPages-1 {
        r.ReadingStats.BooksCompleted++
    }

    // 保存阅读统计
    saveReadingStats(r.FilePath, r.ReadingStats)
}

// highlightSearchTerms 高亮搜索词
func (r *Reader) highlightSearchTerms() {
	// 实现搜索词高亮
	// 这需要在渲染时特殊处理，比较复杂，暂时不实现
}

func loadBookmarksForFile(filePath string) []Bookmark {
	bookmarksPath := getBookmarksPath()

	// 如果书签文件不存在，返回空列表
	if _, err := os.Stat(bookmarksPath); os.IsNotExist(err) {
		return []Bookmark{}
	}

	// 读取书签文件
	file, err := os.Open(bookmarksPath)
	if err != nil {
		return []Bookmark{}
	}
	defer file.Close()

	var allBookmarks []Bookmark
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&allBookmarks); err != nil {
		return []Bookmark{}
	}

	// 过滤出当前文件的书签
	var fileBookmarks []Bookmark
	for _, bookmark := range allBookmarks {
		if bookmark.File == filePath {
			fileBookmarks = append(fileBookmarks, bookmark)
		}
	}

	return fileBookmarks
}

func saveBookmarks(filePath string, bookmarks []Bookmark) error {
	bookmarksPath := getBookmarksPath()

	// 确保目录存在
	bookmarksDir := filepath.Dir(bookmarksPath)
	if err := os.MkdirAll(bookmarksDir, 0755); err != nil {
		return err
	}

	// 读取所有书签
	var allBookmarks []Bookmark
	if _, err := os.Stat(bookmarksPath); !os.IsNotExist(err) {
		file, err := os.Open(bookmarksPath)
		if err == nil {
			defer file.Close()
			decoder := json.NewDecoder(file)
			decoder.Decode(&allBookmarks)
		}
	}

	// 移除当前文件的所有书签
	var newBookmarks []Bookmark
	for _, bookmark := range allBookmarks {
		if bookmark.File != filePath {
			newBookmarks = append(newBookmarks, bookmark)
		}
	}

	// 添加当前文件的新书签
	newBookmarks = append(newBookmarks, bookmarks...)

	// 保存书签
	file, err := os.Create(bookmarksPath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(newBookmarks)
}

func loadNotes(filePath string) []Note {
	notesPath := getNotesPath()

	// 如果笔记文件不存在，返回空列表
	if _, err := os.Stat(notesPath); os.IsNotExist(err) {
		return []Note{}
	}

	// 读取笔记文件
	file, err := os.Open(notesPath)
	if err != nil {
		return []Note{}
	}
	defer file.Close()

	var allNotes map[string][]Note
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&allNotes); err != nil {
		return []Note{}
	}

	// 返回当前文件的笔记
	return allNotes[filePath]
}

func saveNotes(filePath string, notes []Note) error {
	notesPath := getNotesPath()

	// 确保目录存在
	notesDir := filepath.Dir(notesPath)
	if err := os.MkdirAll(notesDir, 0755); err != nil {
		return err
	}

	// 读取所有笔记
	var allNotes map[string][]Note
	if _, err := os.Stat(notesPath); !os.IsNotExist(err) {
		file, err := os.Open(notesPath)
		if err == nil {
			defer file.Close()
			decoder := json.NewDecoder(file)
			decoder.Decode(&allNotes)
		}
	}

	if allNotes == nil {
		allNotes = make(map[string][]Note)
	}

	// 更新当前文件的笔记
	allNotes[filePath] = notes

	// 保存笔记
	file, err := os.Create(notesPath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(allNotes)
}

// loadReadingStats 加载阅读统计
func loadReadingStats(filePath string) *ReadingStats {
    statsPath := getStatsPath()

    // 如果统计文件不存在，返回空统计
    if _, err := os.Stat(statsPath); os.IsNotExist(err) {
        return &ReadingStats{}
    }

    // 读取统计文件
    file, err := os.Open(statsPath)
    if err != nil {
        return &ReadingStats{}
    }
    defer file.Close()

    var allStats map[string]*ReadingStats
    decoder := json.NewDecoder(file)
    if err := decoder.Decode(&allStats); err != nil {
        return &ReadingStats{}
    }

    // 返回当前文件的统计
    if stats, exists := allStats[filePath]; exists {
        return stats
    }

    return &ReadingStats{}
}

// saveReadingStats 保存阅读统计
func saveReadingStats(filePath string, stats *ReadingStats) error {
    statsPath := getStatsPath()

    // 确保目录存在
    statsDir := filepath.Dir(statsPath)
    if err := os.MkdirAll(statsDir, 0755); err != nil {
        return err
    }

    // 读取所有统计
    var allStats map[string]*ReadingStats
    if _, err := os.Stat(statsPath); !os.IsNotExist(err) {
        file, err := os.Open(statsPath)
        if err == nil {
            defer file.Close()
            decoder := json.NewDecoder(file)
            decoder.Decode(&allStats)
        }
    }

    if allStats == nil {
        allStats = make(map[string]*ReadingStats)
    }

    // 更新当前文件的统计
    allStats[filePath] = stats

    // 保存统计
    file, err := os.Create(statsPath)
    if err != nil {
        return err
    }
    defer file.Close()

    encoder := json.NewEncoder(file)
    encoder.SetIndent("", "  ")
    return encoder.Encode(allStats)
}


func getBookmarksPath() string {
	homeDir, _ := os.UserHomeDir()
	return filepath.Join(homeDir, ".config", "novel-reader", "bookmarks.json")
}

func getNotesPath() string {
	homeDir, _ := os.UserHomeDir()
	return filepath.Join(homeDir, ".config", "novel-reader", "notes.json")
}

func getStatsPath() string {
	homeDir, _ := os.UserHomeDir()
	return filepath.Join(homeDir, ".config", "novel-reader", "stats.json")
}

func getFileName(path string) string {
	return filepath.Base(path)
}

// startAutoFlip 启动自动翻页
func (r *Reader) startAutoFlip() {
    // 如果已经启动，先停止
    r.stopAutoFlip()
    
    // 确保间隔大于0
    interval := r.Config.AutoFlipInterval
    if interval <= 0 {
        interval = 5 // 默认5秒
        r.Config.AutoFlipInterval = interval
    }
    
    // 创建计时器和退出通道
    r.AutoFlipTicker = time.NewTicker(time.Duration(interval) * time.Second)
    r.AutoFlipQuit = make(chan struct{})
    
    // 启动goroutine处理自动翻页
    go func() {
        for {
            select {
            case <-r.AutoFlipTicker.C:
                // 如果不是最后一页，翻到下一页
                if r.CurrentPage < r.TotalPages-1 {
                    r.CurrentPage++
                    r.RenderPage()
                } else {
                    // 如果是最后一页，停止自动翻页
                    r.stopAutoFlip()
                    r.Config.AutoFlipEnabled = false
                    saveConfig(r.Config)
                }
            case <-r.AutoFlipQuit:
                if r.AutoFlipTicker != nil {
                    r.AutoFlipTicker.Stop()
                }
                return
            }
        }
    }()
    
    r.Config.AutoFlipEnabled = true
}

// stopAutoFlip 停止自动翻页
func (r *Reader) stopAutoFlip() {
    if r.AutoFlipQuit != nil {
        close(r.AutoFlipQuit)
        r.AutoFlipQuit = nil
    }
    if r.AutoFlipTicker != nil {
        r.AutoFlipTicker.Stop()
        r.AutoFlipTicker = nil
    }
    r.Config.AutoFlipEnabled = false
    fmt.Println("自动翻页已停止")
}

// toggleAutoFlip 切换自动翻页状态
func (r *Reader) toggleAutoFlip() {
	if r.Config.AutoFlipEnabled {
		r.stopAutoFlip()
	} else {
		r.startAutoFlip()
	}
}

// startRemindTimer 启动提醒计时器
func (r *Reader) startRemindTimer() {
    // 如果已经启动，先停止
    r.stopRemindTimer()
    
    interval := time.Duration(r.Config.RemindInterval) * time.Minute
    if interval <= 0 {
        return
    }
    
    // 创建计时器和退出通道
    r.RemindTicker = time.NewTicker(interval)
    r.RemindQuit = make(chan struct{})
    
    // 启动goroutine处理提醒
    go func() {
        for {
            select {
            case <-r.RemindTicker.C:
                r.showRemindAlert()
            case <-r.RemindQuit:
                if r.RemindTicker != nil {
                    r.RemindTicker.Stop()
                }
                return
            }
        }
    }()
}

// stopRemindTimer 停止提醒计时器
func (r *Reader) stopRemindTimer() {
    if r.RemindQuit != nil {
        close(r.RemindQuit)
        r.RemindQuit = nil
    }
    if r.RemindTicker != nil {
        r.RemindTicker.Stop()
        r.RemindTicker = nil
    }
}

// showRemindAlert 显示提醒弹窗
func (r *Reader) showRemindAlert() {
    // 恢复终端状态以显示提醒
    if oldState != nil {
        term.Restore(int(os.Stdin.Fd()), oldState)
    }
    
    defer func() {
        // 恢复原始模式
        if oldState != nil {
            term.MakeRaw(int(os.Stdin.Fd()))
        }
        // 重新渲染页面
        r.RenderPage()
    }()
    
    clearScreen()
    
    // 获取终端大小
    width, height, _ := getTerminalSize()
    
    // 计算弹窗位置和大小
    popupWidth := 50
    popupHeight := 7
    popupX := (width - popupWidth) / 2
    popupY := (height - popupHeight) / 2
    
    // 绘制弹窗边框
    drawPopup(popupX, popupY, popupWidth, popupHeight, r.Config.BorderStyle)
    
    // 显示提醒消息
    message := fmt.Sprintf("已经阅读%d分钟了,休息会眼睛吧!", r.Config.RemindInterval)
    messageX := popupX + (popupWidth-len(message))/2
    displayText(messageX, popupY+2, message, r.Config.FontColor, r.Config.BgColor)
    
    // 显示确认提示
    prompt := "按任意键继续阅读..."
    promptX := popupX + (popupWidth-len(prompt))/2
    displayText(promptX, popupY+4, prompt, r.Config.FontColor, r.Config.BgColor)
    
    // 等待按键
    getInput()
    
    // 重置提醒计时器
    r.stopRemindTimer()
    r.startRemindTimer()
}

// drawPopup 绘制弹窗
func drawPopup(x, y, width, height int, style string) {
    var topLeft, topRight, bottomLeft, bottomRight, horizontal, vertical string

    switch style {
    case "round":
        topLeft, topRight, bottomLeft, bottomRight = "╭", "╮", "╰", "╯"
        horizontal, vertical = "─", "│"
    case "bold":
        topLeft, topRight, bottomLeft, bottomRight = "┏", "┓", "┗", "┛"
        horizontal, vertical = "━", "┃"
    case "double":
        topLeft, topRight, bottomLeft, bottomRight = "╔", "╗", "╚", "╝"
        horizontal, vertical = "═", "║"
    case "thin":
        topLeft, topRight, bottomLeft, bottomRight = "┌", "┐", "└", "┘"
        horizontal, vertical = "─", "│"
    default:
        return // 无边框
    }

    // 绘制上边框
    fmt.Printf("\033[%d;%dH%s", y+1, x+1, topLeft)
    for i := 0; i < width-2; i++ {
        fmt.Print(horizontal)
    }
    fmt.Print(topRight)

    // 绘制左右边框
    for i := 1; i < height-1; i++ {
        fmt.Printf("\033[%d;%dH%s", y+i+1, x+1, vertical)
        fmt.Printf("\033[%d;%dH%s", y+i+1, x+width, vertical)
    }

    // 绘制下边框
    fmt.Printf("\033[%d;%dH%s", y+height, x+1, bottomLeft)
    for i := 0; i < width-2; i++ {
        fmt.Print(horizontal)
    }
    fmt.Print(bottomRight)
}