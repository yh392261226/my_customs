package ui

import (
	"fmt"
	"os"
	"time"
	"ureader/config"

	"github.com/gdamore/tcell/v2"
	"github.com/rivo/tview"
	"golang.org/x/term"
)

// showReadingStats 显示阅读统计
func (ur *UnifiedReader) showReadingStats() {
    stats := config.LoadStats()
    
    switch ur.mode {
    case ModeRawTerminal:
        ur.showReadingStatsRaw(stats)
    case ModeTUI:
        ur.showReadingStatsTUI(stats)
    case ModeSimple:
        ur.showReadingStatsSimple(stats)
    }
}

// showReadingStatsTUI TUI模式显示阅读统计
func (ur *UnifiedReader) showReadingStatsTUI(stats *config.ReadingStats) {
    // 创建统计页面
    pages := tview.NewPages()
    
    // 主统计页面
    mainPage := ur.createStatsMainPage(stats)
    pages.AddPage("main", mainPage, true, true)
    
    // 详细统计页面
    detailPage := ur.createStatsDetailPage(stats)
    pages.AddPage("detail", detailPage, false, false)
    
    // 设置输入处理
    pages.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
        switch event.Key() {
        case tcell.KeyEsc:
            // 直接返回主界面，不进行其他处理
            ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
            return nil
        case tcell.KeyTab:
            // 切换页面
            currentPage, _ := pages.GetFrontPage()
            if currentPage == "main" {
                pages.SwitchToPage("detail")
            } else {
                pages.SwitchToPage("main")
            }
            return nil
        }
        return event
    })
    
    // 使用安全方法设置根页面
    ur.safeSetRoot(pages, pages)
}

// createStatsMainPage 创建主统计页面
func (ur *UnifiedReader) createStatsMainPage(stats *config.ReadingStats) *tview.Flex {
    // 总阅读时间
    totalTime := fmt.Sprintf("总阅读时间: %s", formatDuration(stats.TotalReadingTime))
    totalTimeText := tview.NewTextView().SetText(totalTime)
    
    // 总阅读页数
    totalPages := fmt.Sprintf("总阅读页数: %d", stats.TotalPagesRead)
    totalPagesText := tview.NewTextView().SetText(totalPages)
    
    // 已读书籍
    totalBooks := fmt.Sprintf("已读书籍: %d", stats.TotalBooksRead)
    totalBooksText := tview.NewTextView().SetText(totalBooks)
    
    // 创建布局
    flex := tview.NewFlex().
        SetDirection(tview.FlexRow).
        AddItem(totalTimeText, 1, 0, false).
        AddItem(totalPagesText, 1, 0, false).
        AddItem(totalBooksText, 1, 0, false).
        AddItem(tview.NewTextView().SetText("按 Tab 查看详细统计，按 Esc 返回"), 1, 0, false)
    
    flex.SetBorder(true).SetTitle("阅读统计")
    return flex
}

// createStatsDetailPage 创建详细统计页面
func (ur *UnifiedReader) createStatsDetailPage(stats *config.ReadingStats) *tview.Flex {
    // 题材偏好
    genreText := "题材偏好:\n"
    for genre, count := range stats.GenrePreferences {
        genreText += fmt.Sprintf("  %s: %d页\n", genre, count)
    }
    genreTextView := tview.NewTextView().SetText(genreText)
    
    // 书籍完成率
    completionText := "书籍完成率:\n"
    for _, bookStat := range stats.BookStats {
        completionText += fmt.Sprintf("  %s: %.1f%%\n", bookStat.Title, bookStat.CompletionRate)
    }
    completionTextView := tview.NewTextView().SetText(completionText)
    
    // 创建布局
    flex := tview.NewFlex().
        SetDirection(tview.FlexColumn).
        AddItem(genreTextView, 0, 1, false).
        AddItem(completionTextView, 0, 1, false)
    
    flex.SetBorder(true).SetTitle("详细统计")
    return flex
}

// formatDuration 格式化时间间隔
func formatDuration(d time.Duration) string {
    hours := int(d.Hours())
    minutes := int(d.Minutes()) % 60
    return fmt.Sprintf("%d小时%d分钟", hours, minutes)
}

// showReadingStatsRaw Raw模式显示阅读统计
func (ur *UnifiedReader) showReadingStatsRaw(stats *config.ReadingStats) {
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
    
    // 显示统计信息
    fmt.Printf("阅读统计\n")
    fmt.Printf("========\n\n")
    fmt.Printf("总阅读时间: %s\n", formatDuration(stats.TotalReadingTime))
    fmt.Printf("总阅读页数: %d\n", stats.TotalPagesRead)
    fmt.Printf("已读书籍: %d\n\n", stats.TotalBooksRead)
    
    fmt.Printf("题材偏好:\n")
    for genre, count := range stats.GenrePreferences {
        fmt.Printf("  %s: %d页\n", genre, count)
    }
    
    fmt.Printf("\n书籍完成率:\n")
    for _, bookStat := range stats.BookStats {
        fmt.Printf("  %s: %.1f%%\n", bookStat.Title, bookStat.CompletionRate)
    }
    
    fmt.Printf("\n按任意键继续...")
    getInput()
}

// showReadingStatsSimple Simple模式显示阅读统计
func (ur *UnifiedReader) showReadingStatsSimple(stats *config.ReadingStats) {
    fmt.Printf("阅读统计\n")
    fmt.Printf("========\n\n")
    fmt.Printf("总阅读时间: %s\n", formatDuration(stats.TotalReadingTime))
    fmt.Printf("总阅读页数: %d\n", stats.TotalPagesRead)
    fmt.Printf("已读书籍: %d\n\n", stats.TotalBooksRead)
    
    fmt.Printf("题材偏好:\n")
    for genre, count := range stats.GenrePreferences {
        fmt.Printf("  %s: %d页\n", genre, count)
    }
    
    fmt.Printf("\n书籍完成率:\n")
    for _, bookStat := range stats.BookStats {
        fmt.Printf("  %s: %.1f%%\n", bookStat.Title, bookStat.CompletionRate)
    }
}