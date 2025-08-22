package ui

import (
	"fmt"
	"ureader/config"
)

// runSimpleMode 运行简单模式
func (ur *UnifiedReader) runSimpleMode() error {
    // 简单模式下，直接输出内容到标准输出
    for {
        // 显示当前页内容
        fmt.Printf("《%s》 - 第 %d/%d 页\n\n", ur.fileName, ur.currentPage+1, ur.totalPages)
        fmt.Println(ur.getCurrentPageContent())
        
        // 显示进度
        progress := float64(ur.currentPage+1) / float64(ur.totalPages) * 100
        fmt.Printf("\n进度: %.1f%%", progress)
        
        // 显示导航提示
        if ur.currentPage < ur.totalPages-1 {
            fmt.Printf("\n--- 按回车继续，输入q退出 ---\n")
        } else {
            fmt.Printf("\n--- 已到最后一页，输入q退出 ---\n")
        }

        // 获取用户输入
        var input string
        fmt.Scanln(&input)

        if input == "q" {
            break
        }

        // 下一页
        if ur.currentPage < ur.totalPages-1 {
            ur.nextPage()
        } else {
            break
        }
    }

    return nil
}

// showBookmarksSimple 简单模式显示书签列表
func (ur *UnifiedReader) showBookmarksSimple(bookmarks []*config.Bookmark) {
    fmt.Println("书签列表:")
    for i, bm := range bookmarks {
        fmt.Printf("%d. %s (第%d页)\n", i+1, bm.Label, bm.Page+1)
    }
    fmt.Println("0. 返回")
    
    fmt.Print("请选择: ")
    var choice int
    _, err := fmt.Scan(&choice)
    if err != nil || choice == 0 {
        return
    }
    
    if choice > 0 && choice <= len(bookmarks) {
        ur.currentPage = bookmarks[choice-1].Page
    }
}