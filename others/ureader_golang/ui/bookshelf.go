package ui

import (
	"fmt"
	"os"
	"sort"
	"time"
	"ureader/config"

	"github.com/rivo/tview"
	"golang.org/x/term"
)

// BookshelfItem 书架项目
type BookshelfItem struct {
    FilePath      string
    Title         string
    Progress      float64
    LastRead      time.Time
    Genre         string
    TotalPages    int
    PagesRead     int
}

// showBookshelf 显示书架
func (ur *UnifiedReader) showBookshelf() {
    // 获取所有书籍的统计信息
    stats := config.LoadStats()
    var items []BookshelfItem
    
    for filePath, bookStat := range stats.BookStats {
        items = append(items, BookshelfItem{
            FilePath:   filePath,
            Title:      bookStat.Title,
            Progress:   bookStat.CompletionRate,
            LastRead:   bookStat.LastRead,
            Genre:      bookStat.Genre,
            TotalPages: bookStat.TotalPages,
            PagesRead:  bookStat.PagesRead,
        })
    }
    
    // 按最后阅读时间排序
    sort.Slice(items, func(i, j int) bool {
        return items[i].LastRead.After(items[j].LastRead)
    })
    
    switch ur.mode {
    case ModeRawTerminal:
        ur.showBookshelfRaw(items)
    case ModeTUI:
        ur.showBookshelfTUI(items)
    case ModeSimple:
        ur.showBookshelfSimple(items)
    }
}

// showBookshelfTUI TUI模式显示书架
func (ur *UnifiedReader) showBookshelfTUI(items []BookshelfItem) {
    list := tview.NewList().
        AddItem("返回", "返回阅读", 'b', func() {
			ur.safeSetRoot(ur.tuiPages, ur.tuiTextView)
        })
    
    // 添加书籍到列表
    for i, item := range items {
        // 创建闭包内的局部变量
        currentItem := item
        progress := fmt.Sprintf("%.1f%%", item.Progress)
        lastRead := item.LastRead.Format("2006-01-02")
        
        list.AddItem(
            item.Title,
            fmt.Sprintf("进度: %s, 最后阅读: %s, 题材: %s", progress, lastRead, item.Genre),
            rune('1'+i),
            func() {
                // 打开选中的书籍
                reader, err := NewUnifiedReader(currentItem.FilePath, ur.mode)
                if err != nil {
                    ur.showMessage(fmt.Sprintf("错误: %v", err))
                    return
                }
                
                // 跳转到最后阅读的位置
                progress := config.LoadProgress(currentItem.FilePath)
                if progress.LastPage > 0 {
                    reader.GoToPage(progress.LastPage)
                }
                
                // 运行阅读器
                ur.tuiApp.Stop()
                if err := reader.Run(); err != nil {
                    fmt.Fprintf(os.Stderr, "错误: %v\n", err)
                }
            })
    }
    
    list.SetBorder(true).SetTitle("智能书架")
    ur.safeSetRoot(list, list)
}

// showBookshelfRaw Raw模式显示书架
func (ur *UnifiedReader) showBookshelfRaw(items []BookshelfItem) {
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
    
    if len(items) == 0 {
        fmt.Println("书架为空")
        fmt.Println("\n按任意键继续...")
        getInput()
        return
    }
    
    fmt.Println("智能书架")
    fmt.Println("========")
    fmt.Println()
    
    for i, item := range items {
        progress := fmt.Sprintf("%.1f%%", item.Progress)
        lastRead := item.LastRead.Format("2006-01-02")
        fmt.Printf("%d. %s (进度: %s, 最后阅读: %s, 题材: %s)\n", 
            i+1, item.Title, progress, lastRead, item.Genre)
    }
    
    fmt.Println()
    fmt.Println("0. 返回")
    fmt.Print("请选择: ")
    
    var choice int
    _, err := fmt.Scan(&choice)
    if err != nil || choice == 0 {
        return
    }
    
    if choice > 0 && choice <= len(items) {
        item := items[choice-1]
        
        // 打开选中的书籍
        reader, err := NewUnifiedReader(item.FilePath, ur.mode)
        if err != nil {
            fmt.Fprintf(os.Stderr, "错误: %v\n", err)
            return
        }
        
        // 跳转到最后阅读的位置
        progress := config.LoadProgress(item.FilePath)
        if progress.LastPage > 0 {
            reader.GoToPage(progress.LastPage)
        }
        
        // 运行阅读器
        if err := reader.Run(); err != nil {
            fmt.Fprintf(os.Stderr, "错误: %v\n", err)
        }
    }
}

// showBookshelfSimple Simple模式显示书架
func (ur *UnifiedReader) showBookshelfSimple(items []BookshelfItem) {
    if len(items) == 0 {
        fmt.Println("书架为空")
        return
    }
    
    fmt.Println("智能书架")
    fmt.Println("========")
    fmt.Println()
    
    for i, item := range items {
        progress := fmt.Sprintf("%.1f%%", item.Progress)
        lastRead := item.LastRead.Format("2006-01-02")
        fmt.Printf("%d. %s (进度: %s, 最后阅读: %s, 题材: %s)\n", 
            i+1, item.Title, progress, lastRead, item.Genre)
    }
}