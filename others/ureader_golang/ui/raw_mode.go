package ui

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
	"ureader/config"

	"github.com/mattn/go-runewidth"
	"golang.org/x/term"
)

var oldState *term.State
var isWindowHidden bool = false

// runRawMode 运行原始终端模式
func (ur *UnifiedReader) runRawMode() error {
    // 初始化终端
    if err := initTerminal(); err != nil {
        return err
    }
    defer cleanupTerminal()

    // 主循环
    for {
		// 如果处于隐藏状态，运行shell模拟器
        if ur.isHidden {
            ur.runShellSimulator()
            // 从shell模拟器返回后，重新渲染页面
            ur.renderRawPage()
            continue
        }

        // 渲染页面
        ur.renderRawPage()

        // 处理输入
        key, err := getInput()
        if err != nil {
            return err
        }

        // 处理按键
        switch key {
        case "up", "left", " ", "p":
            ur.previousPage()
        case "down", "right", "n":
            ur.nextPage()
        case "home":
            ur.firstPage()
        case "end":
            ur.lastPage()
        case "g":
            ur.gotoPageRaw()
        case "m":
            ur.addBookmark()
        case "l":
            ur.showBookmarks()
        case "s":
            ur.showSettingsRaw()
        case "/":
            ur.searchRaw()
        case "r":
            ur.toggleReadAloud()
        case "h":
            ur.showHelpRaw()
		case "a":
			ur.toggleAutoFlip()
			if ur.config.AutoFlip {
				ur.showMessageRaw("自动翻页已开启")
			} else {
				ur.showMessageRaw("自动翻页已关闭")
			}
		case "i":
    		ur.isHidden = true
		case "b":
			ur.toggleBookmark()
		case "f":
			ur.listBookmarks()
		case "x":
    		ur.showReadingStats()
		case "t":
    		ur.showBookshelf()
        case "q":
            return nil
        }
    }
}

// firstPage 跳转到第一页
func (ur *UnifiedReader) firstPage() {
    ur.currentPage = 0
}

// lastPage 跳转到最后一页
func (ur *UnifiedReader) lastPage() {
    ur.currentPage = ur.totalPages - 1
}

// renderRawPage 渲染原始模式页面
func (ur *UnifiedReader) renderRawPage() {
    clearScreen()

    // 绘制边框
    if ur.config.BorderStyle != "none" {
        drawBorder(ur.config.BorderStyle, ur.config.Width, ur.config.Height, ur.config.BorderColor, ur.config.BackgroundColor)
    }

    // 计算内容区域
    contentWidth := ur.config.Width - 2*ur.config.Margin - 2*ur.config.Padding - 2 // 减去边框宽度
    contentHeight := ur.config.Height - 2*ur.config.Margin - 2*ur.config.Padding - 4 // 减去边框高度和标题/状态栏

    // 显示标题
    title := fmt.Sprintf("《%s》 - 第 %d/%d 页", ur.fileName, ur.currentPage+1, ur.totalPages)
    if len(title) > contentWidth {
        title = title[:contentWidth]
    }
    titleX := 1 + ur.config.Margin + ur.config.Padding + (contentWidth-len(title))/2
    displayText(titleX, 1+ur.config.Margin+ur.config.Padding, title, ur.config.FontColor, ur.config.BackgroundColor)

    // 显示内容
    content := ur.getCurrentPageContent()
    lines := strings.Split(content, "\n")
    for i, line := range lines {
        if i >= contentHeight {
            break
        }
        // 自动换行处理
        wrappedLines := wrapText(line, contentWidth)
        for j, wrappedLine := range wrappedLines {
            if i+j >= contentHeight {
                break
            }
            y := 2 + i + j + ur.config.Margin + ur.config.Padding
            displayText(1+ur.config.Margin+ur.config.Padding, y, wrappedLine, ur.config.FontColor, ur.config.BackgroundColor)
        }
        i += len(wrappedLines) - 1
    }

    // 显示状态栏
    status := fmt.Sprintf("进度: %.1f%%", float64(ur.currentPage+1)/float64(ur.totalPages)*100)
	help := "[←/→:翻页 g:跳转 m:书签 /:搜索 r:朗读 i:老板键 q:退出]"
    
    displayText(1+ur.config.Margin+ur.config.Padding, ur.config.Height-2-ur.config.Margin-ur.config.Padding, status, ur.config.FontColor, ur.config.BackgroundColor)
    displayText(ur.config.Width-len(help)-1-ur.config.Margin-ur.config.Padding, ur.config.Height-2-ur.config.Margin-ur.config.Padding, help, ur.config.FontColor, ur.config.BackgroundColor)
}

// gotoPageRaw 原始模式的跳转页面
func (ur *UnifiedReader) gotoPageRaw() {
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
    fmt.Print("请输入页码: ")
    
    var input string
    fmt.Scanln(&input)
    
    if page, err := strconv.Atoi(input); err == nil && page > 0 && page <= ur.totalPages {
        ur.currentPage = page - 1
    }
}

// showBookmarksRaw 原始模式显示书签列表
func (ur *UnifiedReader) showBookmarksRaw(bookmarks []*config.Bookmark) {
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
    
    if len(bookmarks) == 0 {
        fmt.Println("没有书签")
        fmt.Println("\n按任意键继续...")
        getInput()
        return
    }
    
    fmt.Println("书签列表:")
    for i, bm := range bookmarks {
        filename := filepath.Base(bm.FilePath)
        fmt.Printf("%d. %s - %s (第%d页)\n", i+1, filename, bm.Label, bm.Page+1)
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

// showSettingsRaw 原始模式显示设置
func (ur *UnifiedReader) showSettingsRaw() {
    selected := 0
    options := []string{
        "字体颜色: " + ur.config.FontColor,
        "背景颜色: " + ur.config.BackgroundColor,
        "边框颜色: " + ur.config.BorderColor,
        "边框样式: " + ur.config.BorderStyle,
        "宽度: " + strconv.Itoa(ur.config.Width),
        "高度: " + strconv.Itoa(ur.config.Height),
        "边距: " + strconv.Itoa(ur.config.Margin),
        "内边距: " + strconv.Itoa(ur.config.Padding),
        "朗读速度: " + strconv.Itoa(ur.config.TTSSpeed),
        "自动朗读: " + strconv.FormatBool(ur.config.AutoReadAloud),
        "自动翻页: " + strconv.FormatBool(ur.config.AutoFlip),
        "自动翻页间隔: " + strconv.Itoa(ur.config.AutoFlipInterval) + "秒",
        "显示进度: " + strconv.FormatBool(ur.config.ShowProgress),
        "提醒间隔: " + strconv.Itoa(ur.config.RemindInterval) + "分钟",
        "保存并退出",
    }
    
    for {
        clearScreen()
        
        // 计算可显示的行数
        _, height, _ := getTerminalSize()
        maxVisible := height - 6 // 保留空间给标题和提示
        
        // 显示标题
        title := "设置 - 使用上下键选择，回车键修改，ESC退出"
        displayText(2, 1, title, ur.config.FontColor, ur.config.BackgroundColor)
        displayText(2, 2, strings.Repeat("=", len(title)), ur.config.FontColor, ur.config.BackgroundColor)
        
        // 计算起始索引以确保选中的项可见
        startIdx := 0
        if selected >= maxVisible {
            startIdx = selected - maxVisible + 1
        }
        endIdx := startIdx + maxVisible
        if endIdx > len(options) {
            endIdx = len(options)
        }
        
        // 显示选项
        for i := startIdx; i < endIdx; i++ {
            y := 4 + (i - startIdx)
            if i == selected {
                displayText(2, y, "> "+options[i], ur.config.FontColor, ur.config.BackgroundColor)
            } else {
                displayText(2, y, "  "+options[i], ur.config.FontColor, ur.config.BackgroundColor)
            }
        }
        
        // 显示滚动提示
        if startIdx > 0 {
            displayText(2, 3, "↑ 更多...", ur.config.FontColor, ur.config.BackgroundColor)
        }
        if endIdx < len(options) {
            displayText(2, height-2, "↓ 更多...", ur.config.FontColor, ur.config.BackgroundColor)
        }
        
        // 显示导航提示
        help := "↑/↓: 选择  Enter: 修改  ESC: 退出"
        displayText(2, height-1, help, ur.config.FontColor, ur.config.BackgroundColor)
        
        // 获取输入
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
			shouldExit := ur.modifySettingRaw(selected)
			if shouldExit {
				return
			}
			// 更新选项显示
			options = []string{
				"字体颜色: " + ur.config.FontColor,
				"背景颜色: " + ur.config.BackgroundColor,
				"边框颜色: " + ur.config.BorderColor,
				"边框样式: " + ur.config.BorderStyle,
				"宽度: " + strconv.Itoa(ur.config.Width),
				"高度: " + strconv.Itoa(ur.config.Height),
				"边距: " + strconv.Itoa(ur.config.Margin),
				"内边距: " + strconv.Itoa(ur.config.Padding),
				"朗读速度: " + strconv.Itoa(ur.config.TTSSpeed),
				"自动朗读: " + strconv.FormatBool(ur.config.AutoReadAloud),
				"自动翻页: " + strconv.FormatBool(ur.config.AutoFlip),
				"自动翻页间隔: " + strconv.Itoa(ur.config.AutoFlipInterval) + "秒",
				"显示进度: " + strconv.FormatBool(ur.config.ShowProgress),
				"提醒间隔: " + strconv.Itoa(ur.config.RemindInterval) + "分钟",
				"保存并退出",
			}
        case "esc":
            // 保存配置
            config.SaveConfig(ur.config)
            return
        }
    }
}

// modifySettingRaw 修改设置项，返回是否退出设置
func (ur *UnifiedReader) modifySettingRaw(selected int) bool {
    switch selected {
    case 0: // 字体颜色
        colors := []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"}
        currentIndex := 0
        for i, color := range colors {
            if color == ur.config.FontColor {
                currentIndex = i
                break
            }
        }
        nextIndex := (currentIndex + 1) % len(colors)
        ur.config.FontColor = colors[nextIndex]
        return false
    case 1: // 背景颜色
        colors := []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "transparent"}
        currentIndex := 0
        for i, color := range colors {
            if color == ur.config.BackgroundColor {
                currentIndex = i
                break
            }
        }
        nextIndex := (currentIndex + 1) % len(colors)
        ur.config.BackgroundColor = colors[nextIndex]
        return false
    case 2: // 边框颜色
        colors := []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "gray"}
        currentIndex := 0
        for i, color := range colors {
            if color == ur.config.BorderColor {
                currentIndex = i
                break
            }
        }
        nextIndex := (currentIndex + 1) % len(colors)
        ur.config.BorderColor = colors[nextIndex]
        return false
    case 3: // 边框样式
        styles := []string{"none", "single", "double", "round", "bold"}
        currentIndex := 0
        for i, style := range styles {
            if style == ur.config.BorderStyle {
                currentIndex = i
                break
            }
        }
        nextIndex := (currentIndex + 1) % len(styles)
        ur.config.BorderStyle = styles[nextIndex]
        return false
    case 4: // 宽度
        input := showInputPrompt("请输入宽度: ")
        if width, err := strconv.Atoi(input); err == nil && width > 0 {
            ur.config.Width = width
        }
        return false
    case 5: // 高度
        input := showInputPrompt("请输入高度: ")
        if height, err := strconv.Atoi(input); err == nil && height > 0 {
            ur.config.Height = height
        }
        return false
    case 6: // 边距
        input := showInputPrompt("请输入边距: ")
        if margin, err := strconv.Atoi(input); err == nil && margin >= 0 {
            ur.config.Margin = margin
        }
        return false
    case 7: // 内边距
        input := showInputPrompt("请输入内边距: ")
        if padding, err := strconv.Atoi(input); err == nil && padding >= 0 {
            ur.config.Padding = padding
        }
        return false
    case 8: // 朗读速度
        input := showInputPrompt("请输入朗读速度 (1-10): ")
        if speed, err := strconv.Atoi(input); err == nil && speed >= 1 && speed <= 10 {
            ur.config.TTSSpeed = speed
        }
        return false
    case 9: // 自动朗读
        ur.config.AutoReadAloud = !ur.config.AutoReadAloud
        return false
    case 10: // 自动翻页
        ur.config.AutoFlip = !ur.config.AutoFlip
        return false
    case 11: // 自动翻页间隔
        input := showInputPrompt("请输入自动翻页间隔(秒): ")
        if interval, err := strconv.Atoi(input); err == nil && interval > 0 {
            ur.config.AutoFlipInterval = interval
        }
        return false
    case 12: // 显示进度
        ur.config.ShowProgress = !ur.config.ShowProgress
        return false
    case 13: // 提醒间隔
        input := showInputPrompt("请输入提醒间隔(分钟): ")
        if interval, err := strconv.Atoi(input); err == nil && interval >= 0 {
            ur.config.RemindInterval = interval
        }
        return false
    case 14: // 保存并退出
        config.SaveConfig(ur.config)
        return true
    default:
        return false
    }
}

// searchRaw 原始模式搜索
func (ur *UnifiedReader) searchRaw() {
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
    searchTerm, _ := reader.ReadString('\n')
    searchTerm = strings.TrimSpace(searchTerm)
    
    if searchTerm == "" {
        return
    }

    // 在所有页面中搜索关键词
    searchResults := []int{}
    for i, page := range ur.content {
        if strings.Contains(page, searchTerm) {
            searchResults = append(searchResults, i)
        }
    }

    if len(searchResults) == 0 {
        clearScreen()
        fmt.Println("未找到匹配结果")
        fmt.Println("\n按任意键继续...")
        getInput()
        return
    }

    // 显示搜索结果
    ur.showSearchResults(searchTerm, searchResults)
}

// showSearchResults 显示搜索结果
func (ur *UnifiedReader) showSearchResults(searchTerm string, results []int) {
    currentResult := 0
    
    for {
        // 恢复终端状态以便正常显示
        if oldState != nil {
            term.Restore(int(os.Stdin.Fd()), oldState)
        }
        
        clearScreen()
        
        // 显示搜索结果信息
        title := fmt.Sprintf("搜索: %s (%d/%d)", searchTerm, currentResult+1, len(results))
        fmt.Println(title)
        fmt.Println(strings.Repeat("=", len(title)))
        
        // 显示当前搜索结果
        if currentResult < len(results) {
            page := results[currentResult]
            content := ur.content[page]
            
            // 高亮显示搜索词
            highlighted := strings.ReplaceAll(content, searchTerm, fmt.Sprintf("\033[1;31m%s\033[0m", searchTerm))
            
            fmt.Printf("第 %d 页:\n", page+1)
            fmt.Println(highlighted)
        }
        
        // 显示导航提示
        fmt.Printf("\n导航: n-下一个, p-上一个, g-跳转, q-退出\n")
        
        // 恢复原始模式以获取输入
        if oldState != nil {
            term.MakeRaw(int(os.Stdin.Fd()))
        }
        
        // 获取输入
        input, err := getInput()
        if err != nil {
            break
        }
        
        // 恢复终端状态以便处理输入
        if oldState != nil {
            term.Restore(int(os.Stdin.Fd()), oldState)
        }
        
        switch input {
        case "n":
            if currentResult < len(results)-1 {
                currentResult++
            }
        case "p":
            if currentResult > 0 {
                currentResult--
            }
        case "g":
            if currentResult < len(results) {
                ur.currentPage = results[currentResult]
                // 恢复原始模式
                if oldState != nil {
                    term.MakeRaw(int(os.Stdin.Fd()))
                }
                return
            }
        case "q":
            // 恢复原始模式
            if oldState != nil {
                term.MakeRaw(int(os.Stdin.Fd()))
            }
            return
        }
    }
}

// 初始化终端
func initTerminal() error {
	if !term.IsTerminal(int(os.Stdin.Fd())) {
		return nil
	}

	var err error
	oldState, err = term.MakeRaw(int(os.Stdin.Fd()))
	return err
}

// 清理终端
func cleanupTerminal() {
	if oldState != nil {
		term.Restore(int(os.Stdin.Fd()), oldState)
	}
}

// 清屏
func clearScreen() {
	fmt.Print("\033[2J\033[H")
}

// 显示文本
func displayText(x, y int, text, fgColor, bgColor string) {
	colorCode := getColorCode(fgColor, bgColor)
	fmt.Printf("\033[%d;%dH%s%s", y+1, x+1, colorCode, text)
}

// 获取颜色代码
func getColorCode(fgColor, bgColor string) string {
    fgCodes := map[string]string{
        "black":   "30",
        "red":     "31",
        "green":   "32",
        "yellow":  "33",
        "blue":    "34",
        "magenta": "35",
        "cyan":    "36",
        "white":   "37",
        "default": "39",
    }

    bgCodes := map[string]string{
        "black":        "40",
        "red":          "41",
        "green":        "42",
        "yellow":       "43",
        "blue":         "44",
        "magenta":      "45",
        "cyan":         "46",
        "white":        "47",
        "default":      "49",
        "transparent":  "", // 透明背景
    }

    fgCode, exists := fgCodes[fgColor]
    if !exists {
        fgCode = "37" // 默认白色
    }

    bgCode, exists := bgCodes[bgColor]
    if !exists {
        bgCode = "40" // 默认黑色
    }

    if bgColor == "transparent" {
        return fmt.Sprintf("\033[%sm", fgCode)
    }

    return fmt.Sprintf("\033[%s;%sm", fgCode, bgCode)
}

// drawBorder 绘制边框
func drawBorder(style string, width, height int, borderColor, bgColor string) {
    var topLeft, topRight, bottomLeft, bottomRight, horizontal, vertical string

    switch style {
    case "single":
        topLeft, topRight, bottomLeft, bottomRight = "┌", "┐", "└", "┘"
        horizontal, vertical = "─", "│"
    case "double":
        topLeft, topRight, bottomLeft, bottomRight = "╔", "╗", "╚", "╝"
        horizontal, vertical = "═", "║"
    case "round":
        topLeft, topRight, bottomLeft, bottomRight = "╭", "╮", "╰", "╯"
        horizontal, vertical = "─", "│"
    case "bold":
        topLeft, topRight, bottomLeft, bottomRight = "┏", "┓", "┗", "┛"
        horizontal, vertical = "━", "┃"
    default:
        return // 不绘制边框
    }

    // 绘制上边框
    displayText(1, 1, topLeft, borderColor, bgColor)
    for x := 2; x < width; x++ {
        displayText(x, 1, horizontal, borderColor, bgColor)
    }
    displayText(width, 1, topRight, borderColor, bgColor)

    // 绘制左右边框
    for y := 2; y < height; y++ {
        displayText(1, y, vertical, borderColor, bgColor)
        displayText(width, y, vertical, borderColor, bgColor)
    }

    // 绘制下边框
    displayText(1, height, bottomLeft, borderColor, bgColor)
    for x := 2; x < width; x++ {
        displayText(x, height, horizontal, borderColor, bgColor)
    }
    displayText(width, height, bottomRight, borderColor, bgColor)
}

// 获取输入
func getInput() (string, error) {
    buffer := make([]byte, 10)
    n, err := os.Stdin.Read(buffer)
    if err != nil {
        return "", err
    }

    // 解析特殊按键
    if n >= 3 && buffer[0] == 27 && buffer[1] == 91 {
        switch buffer[2] {
        case 65:
            return "up", nil
        case 66:
            return "down", nil
        case 67:
            return "right", nil
        case 68:
            return "left", nil
        case 72: // Home键
            return "home", nil
        case 70: // End键
            return "end", nil
        }
    } else if n == 1 {
        switch buffer[0] {
        case 27: // ESC键
            return "esc", nil
        case 32:
            return " ", nil
        case 113:
            return "q", nil
        case 115:
            return "s", nil
        case 104:
            return "h", nil
        case 109:
            return "m", nil
        case 108:
            return "l", nil
        case 103:
            return "g", nil
		case 105: // 'i' 键
    		return "i", nil
        case 114:
            return "r", nil
        case 47:
            return "/", nil
		case 97: // 'a' 键
    		return "a", nil
        case 13: // Enter键
            return "enter", nil
        }
    }

    return string(buffer[:n]), nil
}

// 显示输入提示
func showInputPrompt(prompt string) string {
    // 先恢复终端状态，以便正常回显
    if oldState != nil {
        term.Restore(int(os.Stdin.Fd()), oldState)
    }
    
    defer func() {
        // 输入完成后重新设置原始模式
        if oldState != nil {
            term.MakeRaw(int(os.Stdin.Fd()))
        }
    }()
    
    // 清屏并显示提示
    clearScreen()
    fmt.Print(prompt)
    
    // 使用 bufio.Reader 读取输入，避免问题
    reader := bufio.NewReader(os.Stdin)
    input, _ := reader.ReadString('\n')
    return strings.TrimSpace(input)
}

// showHelpRaw 原始模式显示帮助
func (ur *UnifiedReader) showHelpRaw() {
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
    
    helpLines := []string{
        "统一终端阅读器 - 帮助",
        "====================",
        "",
        "导航:",
        "  空格, →, n: 下一页",
        "  ←, p: 上一页",
        "  Home: 第一页",
        "  End: 最后一页",
        "  g: 跳转到指定页面",
        "",
        "书签:",
        "  m: 添加书签",
        "  l: 显示书签列表",
        "",
        "搜索:",
        "  /: 搜索文本",
        "",
        "朗读:",
        "  r: 朗读/停止朗读当前页",
        "",
        "自动翻页:",
        "  a: 开启/关闭自动翻页",
        "",
        "设置:",
        "  s: 打开设置",
        "",
        "老板键:",
        "  i: 一键隐藏/显示阅读器",
        "",
        "其他:",
        "  h: 显示帮助",
        "  q: 退出阅读器",
        "",
        "自动功能:",
        "  - 自动翻页: 按配置间隔自动翻页",
        "  - 阅读提醒: 按配置间隔提醒休息",
        "",
        "按任意键继续...",
    }
    
    // 逐行显示帮助文本，确保格式正确
    for _, line := range helpLines {
        fmt.Println(line)
    }
    
    getInput()
}


// showHelpTUI 原始模式显示帮助
func (ur *UnifiedReader) showHelpTUI() {
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
    
    helpLines := []string{
        "统一终端阅读器 - 帮助",
        "====================",
        "",
        "导航:",
        "  空格, →, n: 下一页",
        "  ←, p: 上一页",
        "  Home: 第一页",
        "  End: 最后一页",
        "  g: 跳转到指定页面",
        "",
        "书签:",
        "  m: 添加书签",
        "  l: 显示书签列表",
        "",
        "搜索:",
        "  /: 搜索文本",
        "",
        "朗读:",
        "  r: 朗读/停止朗读当前页",
        "",
        "设置:",
        "  s: 打开设置",
        "",
        "其他:",
        "  h: 显示帮助",
        "  q: 退出阅读器",
        "",
        "自动功能:",
        "  - 自动翻页: 按配置间隔自动翻页",
        "  - 阅读提醒: 按配置间隔提醒休息",
        "",
        "按任意键继续...",
    }
    
    // 逐行显示帮助文本，确保格式正确
    for _, line := range helpLines {
        fmt.Println(line)
    }
    
    getInput()
}

// wrapText 文本换行处理
func wrapText(text string, width int) []string {
    var lines []string
    var currentLine strings.Builder
    currentWidth := 0

    for _, r := range text {
        runeWidth := runewidth.RuneWidth(r)

        // 处理换行符
        if r == '\n' {
            lines = append(lines, currentLine.String())
            currentLine.Reset()
            currentWidth = 0
            continue
        }

        // 如果当前字符会使行超出宽度，则换行
        if currentWidth+runeWidth > width {
            lines = append(lines, currentLine.String())
            currentLine.Reset()
            currentWidth = 0
        }

        currentLine.WriteRune(r)
        currentWidth += runeWidth
    }

    if currentLine.Len() > 0 {
        lines = append(lines, currentLine.String())
    }

    return lines
}

// showMessageRaw Raw模式显示消息
func (ur *UnifiedReader) showMessageRaw(message string) {
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
    fmt.Println(message)
    fmt.Println("按任意键继续...")
    getInput()
}

// hideRawReader 隐藏Raw模式阅读器
func (ur *UnifiedReader) hideRawReader() {
    // 恢复终端状态
    if oldState != nil {
        term.Restore(int(os.Stdin.Fd()), oldState)
    }
    
    // 清屏并显示伪终端界面
    clearScreen()
    fmt.Println("$ ")
    
    // 启动一个简单的shell模拟器
    go ur.runShellSimulator()
}

// showRawReader 显示Raw模式阅读器
func (ur *UnifiedReader) showRawReader() {
    // 停止shell模拟器
    // 重新初始化终端
    if oldState != nil {
        term.MakeRaw(int(os.Stdin.Fd()))
    }
    
    // 重新渲染页面
    ur.renderRawPage()
}

// runShellSimulator 运行shell模拟器
func (ur *UnifiedReader) runShellSimulator() {
    // 恢复终端状态以便正常输入
    if oldState != nil {
        term.Restore(int(os.Stdin.Fd()), oldState)
    }
    
    // 清屏并显示提示符
    clearScreen()
    fmt.Print("$ ")
    
    scanner := bufio.NewScanner(os.Stdin)
    
    for ur.isHidden {
        if scanner.Scan() {
            input := scanner.Text()
            
            // 检查是否是恢复命令
            if input == "i" {
                ur.isHidden = false
                // 重新设置原始模式
                if oldState != nil {
                    term.MakeRaw(int(os.Stdin.Fd()))
                }
                return
            }
            
            // 执行简单的shell命令模拟
            ur.executeShellCommand(input)
            fmt.Print("$ ")
        }
    }
}

// executeShellCommand 执行shell命令模拟
func (ur *UnifiedReader) executeShellCommand(command string) {
    // 简单的命令模拟
    switch command {
    case "ls", "dir":
        fmt.Println("file1.txt  file2.txt  documents/  downloads/")
    case "pwd":
        fmt.Println("/home/user")
    case "whoami":
        fmt.Println("user")
    case "date":
        fmt.Println(time.Now().Format("Mon Jan 2 15:04:05 MST 2006"))
    case "exit", "quit":
        fmt.Println("Use 'i' to return to reader")
    case "":
        // 空命令，不做任何事情
    default:
        fmt.Printf("bash: %s: command not found\n", command)
    }
}