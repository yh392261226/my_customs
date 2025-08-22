package ui

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"ureader/config"
	"ureader/core"
	"ureader/tts"

	"github.com/mattn/go-isatty"
	"github.com/rivo/tview"
	"golang.org/x/term"
)

// UnifiedReader 统一阅读器
type UnifiedReader struct {
    mode            RunMode
    book            core.Book
    filePath        string
    fileName        string
    content         []string
    currentPage     int
    totalPages      int
    ttsPlayer       *tts.TTSPlayer
    config          *config.Config
    autoFlipTicker  *time.Ticker
    autoFlipQuit    chan struct{}
    remindTicker    *time.Ticker
    remindQuit      chan struct{}
    // TUI模式组件引用
    tuiApp          *tview.Application
    tuiTextView     *tview.TextView
    tuiFlex         *tview.Flex
    tuiTitleBar     *tview.TextView
    tuiStatusBar    *tview.TextView
    tuiPages        *tview.Pages
    // 老板键状态
    isHidden        bool
}

// NewUnifiedReader 创建统一阅读器
func NewUnifiedReader(filePath string, mode RunMode) (*UnifiedReader, error) {
    // 自动检测模式
    if mode == ModeAuto {
        mode = determineRunMode()
    }

    // 打开书籍
    book, err := core.OpenBook(filePath)
    if err != nil {
        return nil, err
    }

    // 获取内容
    content, err := book.GetContent()
    if err != nil {
        book.Close()
        return nil, err
    }

    // 加载配置
    cfg := config.LoadConfig()

    // 创建阅读器
    ur := &UnifiedReader{
        mode:        mode,
        book:        book,
        filePath:    filePath,
        fileName:    filepath.Base(filePath),
        content:     content,
        totalPages:  len(content),
        ttsPlayer:   tts.NewTTSPlayer(),
        config:      cfg,
    }

    // 加载阅读进度
    ur.loadProgress()
    // 创建TUI页面容器
    ur.tuiPages = tview.NewPages()
    return ur, nil
}

// Run 运行阅读器
func (ur *UnifiedReader) Run() error {
    defer ur.book.Close()
    defer ur.saveProgress()
    defer ur.stopAutoFlip()
    defer ur.stopRemindTimer()

    // 开始阅读时间
    startTime := time.Now()
    
    // 如果配置了自动翻页，启动它
    if ur.config.AutoFlip && ur.config.AutoFlipInterval > 0 {
        ur.startAutoFlip()
    }

    // 如果配置了提醒，启动提醒计时器
    if ur.config.RemindInterval > 0 {
        ur.startRemindTimer()
    }

    var err error
    switch ur.mode {
    case ModeRawTerminal:
        err = ur.runRawMode()
    case ModeTUI:
        err = ur.runTUIMode()
    case ModeSimple:
        err = ur.runSimpleMode()
    default:
        err = ur.runRawMode()
    }
    
    // 更新阅读统计
    readingTime := time.Since(startTime)
    // 暂时使用固定题材
    genre := "未知"

    // 更新阅读统计
    config.UpdateReadingStats(
        ur.filePath,
        ur.fileName,
        ur.currentPage+1, // 假设从0开始计数
        ur.totalPages,
        readingTime,
        genre, // 暂时使用固定值
    )
    
    return err
}

// startAutoFlip 启动自动翻页
func (ur *UnifiedReader) startAutoFlip() {
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
                if ur.currentPage < ur.totalPages-1 {
                    ur.currentPage++
                    // 根据模式重新渲染页面
                    switch ur.mode {
                    case ModeRawTerminal:
                        ur.renderRawPage()
                    case ModeTUI:
                        // TUI模式需要特殊处理
                    }
                } else {
                    ur.stopAutoFlip()
                }
            case <-ur.autoFlipQuit:
                return
            }
        }
    }()
}

// startRemindTimer 启动提醒计时器
func (ur *UnifiedReader) startRemindTimer() {
    ur.stopRemindTimer()
    
    // 确保间隔是正数
    if ur.config.RemindInterval <= 0 {
        return // 如果间隔为0或负数，不启动提醒
    }
    
    interval := time.Duration(ur.config.RemindInterval) * time.Minute
    ur.remindTicker = time.NewTicker(interval)
    ur.remindQuit = make(chan struct{})
    
    go func() {
        for {
            select {
            case <-ur.remindTicker.C:
                ur.showRemind()
            case <-ur.remindQuit:
                return
            }
        }
    }()
}

// stopAutoFlip 停止自动翻页
func (ur *UnifiedReader) stopAutoFlip() {
    if ur.autoFlipTicker != nil {
        ur.autoFlipTicker.Stop()
        ur.autoFlipTicker = nil
    }
    if ur.autoFlipQuit != nil {
        close(ur.autoFlipQuit)
        ur.autoFlipQuit = nil
    }
}

// stopRemindTimer 停止提醒计时器
func (ur *UnifiedReader) stopRemindTimer() {
    if ur.remindTicker != nil {
        ur.remindTicker.Stop()
        ur.remindTicker = nil
    }
    if ur.remindQuit != nil {
        close(ur.remindQuit)
        ur.remindQuit = nil
    }
}

// showRemind 显示提醒
func (ur *UnifiedReader) showRemind() {
    // 根据模式显示提醒
    switch ur.mode {
    case ModeRawTerminal:
        ur.showRemindRaw()
    case ModeTUI:
        // 这里需要传递额外的参数，但我们需要修改方法签名
        // 暂时留空，因为TUI模式的提醒显示已经在TUI模式的处理中实现了
    case ModeSimple:
        fmt.Println("已经阅读了一段时间，建议休息一下")
    }
}

// showRemindRaw 原始模式显示提醒
func (ur *UnifiedReader) showRemindRaw() {
    // 恢复终端状态
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
    fmt.Printf("已经阅读了 %d 分钟，建议休息一下\n", ur.config.RemindInterval)
    fmt.Println("按任意键继续...")
    getInput()
    
    // 重新启动提醒计时器
    ur.startRemindTimer()
}

// GoToPage 跳转到指定页面
func (ur *UnifiedReader) GoToPage(page int) {
	if page >= 0 && page < ur.totalPages {
		ur.currentPage = page
	}
}

// 下一页
func (ur *UnifiedReader) nextPage() {
	if ur.currentPage < ur.totalPages-1 {
		ur.currentPage++
	}
}

// 上一页
func (ur *UnifiedReader) previousPage() {
	if ur.currentPage > 0 {
		ur.currentPage--
	}
}

// 加载阅读进度
func (ur *UnifiedReader) loadProgress() {
	progress := config.LoadProgress(ur.filePath)
	if progress.LastPage > 0 && progress.LastPage < ur.totalPages {
		ur.currentPage = progress.LastPage
	}
}

// 保存阅读进度
func (ur *UnifiedReader) saveProgress() {
	progress := &config.ReadingProgress{
		FilePath:   ur.filePath,
		LastPage:   ur.currentPage,
		TotalPages: ur.totalPages,
	}
	config.SaveProgress(progress)
}

// getCurrentPageContent 获取当前页面内容
func (ur *UnifiedReader) getCurrentPageContent() string {
    if ur.currentPage < len(ur.content) {
        return ur.content[ur.currentPage]
    }
    return "内容不可用"
}

// toggleReadAloud 切换朗读状态
func (ur *UnifiedReader) toggleReadAloud() {
    // 恢复终端状态
    if oldState != nil {
        term.Restore(int(os.Stdin.Fd()), oldState)
    }
    
    // 确保在函数退出时恢复原始模式
    defer func() {
        if oldState != nil {
            term.MakeRaw(int(os.Stdin.Fd()))
        }
    }()
    
    if ur.ttsPlayer.IsPlaying() {
        ur.ttsPlayer.Stop()
        fmt.Println("朗读已停止")
        fmt.Println("按任意键继续...")
        getInput()
    } else {
        // 朗读当前页内容
        text := ur.getCurrentPageContent()
        
        // 清理文本：移除控制字符和特殊符号
        text = cleanTextForTTS(text)
        
        // 限制文本长度，避免TTS命令过长
        if len(text) > 500 {
            text = text[:500] + "..."
        }
        
        err := ur.ttsPlayer.PlayText(text, ur.config.TTSSpeed)
        if err != nil {
            fmt.Printf("TTS错误: %v\n", err)
            fmt.Println("按任意键继续...")
            getInput()
        } else {
            fmt.Println("开始朗读...按任意键停止")
            // 等待用户按键停止
            getInput()
            ur.ttsPlayer.Stop()
        }
    }
}

// 添加书签
func (ur *UnifiedReader) addBookmark() {
	label := fmt.Sprintf("第%d页", ur.currentPage+1)
	bookmark := &config.Bookmark{
		FilePath: ur.filePath,
		Page:     ur.currentPage,
		Label:    label,
	}
	config.AddBookmark(bookmark)
}

// 显示书签列表
func (ur *UnifiedReader) showBookmarks() {
	bookmarks := config.LoadBookmarks()
	// 过滤当前文件的书签
	var fileBookmarks []*config.Bookmark
	for _, bm := range bookmarks {
		if bm.FilePath == ur.filePath {
			fileBookmarks = append(fileBookmarks, bm)
		}
	}
	
	// 根据模式显示书签列表
	switch ur.mode {
	case ModeRawTerminal:
		ur.showBookmarksRaw(fileBookmarks)
	case ModeTUI:
		// TUI模式的书签显示已经在TUI模式的处理中实现了
		// 这里不需要额外处理
	case ModeSimple:
		ur.showBookmarksSimple(fileBookmarks)
	}
}

// 显示设置
func (ur *UnifiedReader) showSettings() {
    switch ur.mode {
    case ModeRawTerminal:
        ur.showSettingsRaw()
    case ModeTUI:
        // TUI模式的设置功能已经在TUI模式的处理中实现了
        // 这里不需要额外处理
    case ModeSimple:
        // 简单模式下不显示设置
        fmt.Println("简单模式下无法更改设置")
    }
}

// 搜索
func (ur *UnifiedReader) search() {
    switch ur.mode {
    case ModeRawTerminal:
        ur.searchRaw()
    case ModeTUI:
        // TUI模式的搜索功能已经在TUI模式的处理中实现了
        // 这里不需要额外处理
    case ModeSimple:
        // 简单模式下不支持搜索
        fmt.Println("简单模式下不支持搜索")
    }
}

// 根据环境确定运行模式
func determineRunMode() RunMode {
	// 检查是否在终端中运行
	if isatty.IsTerminal(os.Stdout.Fd()) {
		// 检查终端是否支持高级功能
		if isAdvancedTerminal() {
			return ModeRawTerminal
		} else {
			return ModeTUI
		}
	} else {
		// 在脚本或管道中运行时使用简单模式
		return ModeSimple
	}
}

// 检查终端是否支持高级功能
func isAdvancedTerminal() bool {
	// 检查终端是否支持原始模式和高级功能
	term := os.Getenv("TERM")
	return term != "dumb" && term != ""
}

// toggleAutoFlip 切换自动翻页状态
func (ur *UnifiedReader) toggleAutoFlip() {
    ur.config.AutoFlip = !ur.config.AutoFlip
    config.SaveConfig(ur.config)
    
    if ur.config.AutoFlip {
        // 根据模式启动自动翻页
        switch ur.mode {
        case ModeRawTerminal:
            ur.startAutoFlip()
        case ModeTUI:
            if ur.tuiApp != nil {
                ur.startAutoFlipTUI(ur.tuiApp)
            }
        }
    } else {
        ur.stopAutoFlip()
    }
}

// cleanTextForTTS 清理文本，移除控制字符和特殊符号
func cleanTextForTTS(text string) string {
    // 移除控制字符
    text = strings.Map(func(r rune) rune {
        if r >= 32 && r != 127 || r == '\n' || r == '\t' {
            return r
        }
        return -1
    }, text)
    
    // 移除常见的特殊符号
    specialChars := []string{"\"", "'", "`", "\\", "|", "~", "^", "<", ">", "{", "}", "[", "]", "(", ")"}
    for _, char := range specialChars {
        text = strings.ReplaceAll(text, char, "")
    }
    
    return text
}

// toggleBookmark 切换书签状态
func (ur *UnifiedReader) toggleBookmark() {
    bookmarks := config.LoadBookmarks()
    
    // 检查是否已存在书签
    for i, bm := range bookmarks {
        if bm.FilePath == ur.filePath && bm.Page == ur.currentPage {
            // 删除书签
            bookmarks = append(bookmarks[:i], bookmarks[i+1:]...)
            config.SaveBookmarks(bookmarks)
            ur.showMessage("书签已删除")
            return
        }
    }
    
    // 添加新书签
    label := fmt.Sprintf("第%d页", ur.currentPage+1)
    bookmark := &config.Bookmark{
        FilePath:   ur.filePath,
        Page:       ur.currentPage,
        Label:      label,
        CreatedAt:  time.Now(),
        UpdatedAt:  time.Now(),
        IsFavorite: false,
        Category:   "默认",
    }
    
    bookmarks = append(bookmarks, bookmark)
    config.SaveBookmarks(bookmarks)
    ur.showMessage("书签已添加")
}

// listBookmarks 列出书签
func (ur *UnifiedReader) listBookmarks() {
    bookmarks := config.LoadBookmarks()
    
    // 过滤当前文件的书签
    var fileBookmarks []*config.Bookmark
    for _, bm := range bookmarks {
        if bm.FilePath == ur.filePath {
            fileBookmarks = append(fileBookmarks, bm)
        }
    }
    
    // 根据模式显示书签列表
    switch ur.mode {
    case ModeRawTerminal:
        ur.showBookmarksRaw(fileBookmarks)
    case ModeTUI:
        ur.showBookmarksTUI(fileBookmarks) // 传递参数
    case ModeSimple:
        ur.showBookmarksSimple(fileBookmarks)
    }
}

// safeSetRoot 安全地设置根页面
func (ur *UnifiedReader) safeSetRoot(root tview.Primitive, focus tview.Primitive) {
    if ur.tuiApp != nil {
        ur.tuiApp.SetRoot(root, true)
        if focus != nil {
            ur.tuiApp.SetFocus(focus)
        }
    }
}

// toggleBossKey 切换老板键状态
func (ur *UnifiedReader) toggleBossKey() {
    ur.isHidden = !ur.isHidden
    
    if ur.isHidden {
        ur.hideReader()
    } else {
        ur.showReader()
    }
}

// hideReader 隐藏阅读器
func (ur *UnifiedReader) hideReader() {
    switch ur.mode {
    case ModeRawTerminal:
        // Raw模式下不需要额外处理，runRawMode会处理
    case ModeTUI:
        // TUI模式下切换到终端界面
        if ur.tuiPages != nil && ur.tuiApp != nil {
            ur.tuiPages.SwitchToPage("terminal")
            // 设置焦点到终端界面
            if terminal := ur.getPagePrimitive("terminal"); terminal != nil {
                ur.tuiApp.SetFocus(terminal)
            }
        }
    case ModeSimple:
        // 简单模式下不需要隐藏
        ur.isHidden = false
    }
}

// showReader 显示阅读器
func (ur *UnifiedReader) showReader() {
    switch ur.mode {
    case ModeRawTerminal:
        // Raw模式下不需要额外处理，runRawMode会处理
    case ModeTUI:
        // TUI模式下切换回主界面
        if ur.tuiPages != nil && ur.tuiApp != nil {
            ur.tuiPages.SwitchToPage("main")
            ur.tuiApp.SetFocus(ur.tuiTextView)
            ur.updateTUI()
        }
    case ModeSimple:
        // 简单模式下不需要特殊处理
    }
}
