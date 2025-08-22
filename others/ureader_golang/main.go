package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"ureader/config"
	"ureader/ui"

	"github.com/mattn/go-isatty"
)

var (
	modeFlag    string
	pageFlag    int
	showHelp    bool
	showVersion bool
)

func init() {
	flag.StringVar(&modeFlag, "mode", "auto", "运行模式: auto, raw, tui, simple")
	flag.IntVar(&pageFlag, "page", 0, "跳转到指定页码")
	flag.BoolVar(&showHelp, "help", false, "显示帮助信息")
	flag.BoolVar(&showVersion, "version", false, "显示版本信息")
	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "用法: %s [选项] <文件路径>\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "选项:\n")
		flag.PrintDefaults()
		fmt.Fprintf(os.Stderr, "\n快捷键:\n")
		fmt.Fprintf(os.Stderr, "  空格, →, n: 下一页\n")
		fmt.Fprintf(os.Stderr, "  ←, p: 上一页\n")
		fmt.Fprintf(os.Stderr, "  g: 跳转页面\n")
		fmt.Fprintf(os.Stderr, "  /: 搜索\n")
		fmt.Fprintf(os.Stderr, "  m: 添加书签\n")
		fmt.Fprintf(os.Stderr, "  l: 显示书签列表\n")
		fmt.Fprintf(os.Stderr, "  s: 设置\n")
		fmt.Fprintf(os.Stderr, "  q: 退出\n")
	}
}

func main() {
	flag.Parse()

	if showVersion {
		fmt.Println("统一终端阅读器 v1.0.0")
		return
	}

	if showHelp {
		flag.Usage()
		return
	}

	args := flag.Args()
	if len(args) == 0 {
		// 没有文件参数，显示书签选择界面
		showBookmarkSelection()
		return
	}

	filePath := args[0]
	mode := parseMode(modeFlag)

	// 创建阅读器
	reader, err := ui.NewUnifiedReader(filePath, mode)
	if err != nil {
		fmt.Fprintf(os.Stderr, "错误: %v\n", err)
		os.Exit(1)
	}

	// 跳转到指定页面
	if pageFlag > 0 {
		reader.GoToPage(pageFlag - 1)
	}

	// 运行阅读器
	if err := reader.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "错误: %v\n", err)
		os.Exit(1)
	}
}

func parseMode(modeStr string) ui.RunMode {
	switch strings.ToLower(modeStr) {
	case "raw":
		return ui.ModeRawTerminal
	case "tui":
		return ui.ModeTUI
	case "simple":
		return ui.ModeSimple
	default:
		return ui.ModeAuto
	}
}

func determineRunMode() ui.RunMode {
	// 检查是否在终端中运行
	if isatty.IsTerminal(os.Stdout.Fd()) {
		// 检查终端是否支持高级功能
		if isAdvancedTerminal() {
			return ui.ModeRawTerminal
		} else {
			return ui.ModeTUI
		}
	} else {
		// 在脚本或管道中运行时使用简单模式
		return ui.ModeSimple
	}
}

func isAdvancedTerminal() bool {
	// 检查终端是否支持原始模式和高级功能
	term := os.Getenv("TERM")
	return term != "dumb" && term != ""
}

func showBookmarkSelection() {
	// 加载书签
	bookmarks := config.LoadBookmarks()
	if len(bookmarks) == 0 {
		fmt.Println("没有书签，请指定一个文件路径")
		fmt.Printf("用法: %s <文件路径>\n", os.Args[0])
		return
	}

	// 显示书签列表
	fmt.Println("请选择一个书签:")
	for i, bm := range bookmarks {
		filename := filepath.Base(bm.FilePath)
		fmt.Printf("%d. %s (第%d页)\n", i+1, filename, bm.Page+1)
	}
	fmt.Println("0. 退出")

	// 获取用户选择
	var choice int
	fmt.Print("请选择: ")
	_, err := fmt.Scan(&choice)
	if err != nil || choice == 0 {
		return
	}

	if choice > 0 && choice <= len(bookmarks) {
		bm := bookmarks[choice-1]
		// 创建阅读器并跳转到书签位置
		reader, err := ui.NewUnifiedReader(bm.FilePath, determineRunMode())
		if err != nil {
			fmt.Fprintf(os.Stderr, "错误: %v\n", err)
			return
		}
		reader.GoToPage(bm.Page)
		reader.Run()
	}
}