package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// Config 阅读器配置
type Config struct {
	Width         int
	Height        int
	FontSize      int
	FontColor     string
	BgColor       string
	BorderStyle   string
	ShowProgress  bool
	Margin        int
	Padding       int
	LineSpacing   int
	TTSSpeed      int
	AutoReadAloud bool
	AutoFlipInterval int    // 自动翻页间隔（秒）
	AutoFlipEnabled  bool   // 自动翻页是否启用
	RemindInterval   int    // 阅读提醒间隔（分钟）
}

// Bookmark 书签结构
type Bookmark struct {
	File  string `json:"file"`
	Page  int    `json:"page"`
	Label string `json:"label"`
}

// 默认配置
var defaultConfig = Config{
	Width:         80,
	Height:        24,
	FontSize:      12,
	FontColor:     "white",
	BgColor:       "black",
	BorderStyle:   "round",
	ShowProgress:  true,
	Margin:        1,
	Padding:       1,
	LineSpacing:   1,
	TTSSpeed:      5,
	AutoReadAloud: false,
	AutoFlipInterval: 5,    // 默认5秒
	AutoFlipEnabled:  false, // 默认禁用
	RemindInterval:   0,    // 默认不提醒
}

func main() {
	if len(os.Args) > 1 {
		// 非交互模式，直接打开指定文件
		filePath := os.Args[1]
		startReaderWithFile(filePath)
	} else {
		// 交互模式，显示书签列表或空状态
		startInteractiveMode()
	}
}

func startReaderWithFile(filePath string) {
	// 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		fmt.Printf("文件不存在: %s\n", filePath)
		os.Exit(1)
	}
	
	// 检测文件格式
	bookType := detectBookType(filePath)
	if bookType == BookTypeUnknown {
		fmt.Printf("不支持的格式: %s\n", filePath)
		os.Exit(1)
	}
	
	// 初始化阅读器
	reader, err := NewReader(filePath)
	if err != nil {
		fmt.Printf("无法打开文件: %v\n", err)
		os.Exit(1)
	}
	
	// 启动阅读器
	if err := reader.Run(); err != nil {
		fmt.Printf("阅读器错误: %v\n", err)
		os.Exit(1)
	}
}

func startInteractiveMode() {
	// 显示书签列表或空状态
	bookmarks := loadBookmarks()
	if len(bookmarks) == 0 {
		fmt.Println("没有书签，请指定一个小说文件")
		fmt.Println("用法: novel-reader <文件路径>")
		os.Exit(0)
	}
	
	// 显示书签选择界面
	selectedFile := showBookmarkSelection(bookmarks)
	if selectedFile != "" {
		startReaderWithFile(selectedFile)
	}
}

func loadBookmarks() []Bookmark {
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
	
	var bookmarks []Bookmark
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&bookmarks); err != nil {
		return []Bookmark{}
	}
	
	return bookmarks
}

func showBookmarkSelection(bookmarks []Bookmark) string {
	if len(bookmarks) == 0 {
		return ""
	}
	
	fmt.Println("请选择一个书签:")
	fmt.Println("================")
	
	for i, bookmark := range bookmarks {
		label := bookmark.Label
		if label == "" {
			label = fmt.Sprintf("第%d页", bookmark.Page+1)
		}
		fmt.Printf("%d. %s (%s)\n", i+1, label, filepath.Base(bookmark.File))
	}
	
	fmt.Println("0. 退出")
	fmt.Print("请选择: ")
	
	var choice int
	_, err := fmt.Scan(&choice)
	if err != nil || choice < 0 || choice > len(bookmarks) {
		return ""
	}
	
	if choice == 0 {
		return ""
	}
	
	return bookmarks[choice-1].File
}