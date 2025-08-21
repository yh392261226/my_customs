package main

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"time"

	"github.com/mattn/go-runewidth"
	"golang.org/x/term"
)

var oldState *term.State
var isWindowHidden bool = false

// 初始化终端UI
func initUI() error {
	// 检查标准输入是否是终端设备
	if !term.IsTerminal(int(os.Stdin.Fd())) {
		return nil // 不是终端设备，跳过设置
	}

	// 切换到原始模式并保存原始终端状态
	var err error
	oldState, err = term.MakeRaw(int(os.Stdin.Fd()))
	if err != nil {
		return err
	}

	return nil
}

// 清理UI，恢复终端状态
func cleanupUI() {
	// 恢复原始终端状态
	if oldState != nil {
		term.Restore(int(os.Stdin.Fd()), oldState)
	}
}

// 清屏
func clearScreen() {
	fmt.Print("\033[2J\033[H")
}

// 绘制边框
func drawBorder(style string, width, height int) {
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
	case "none":
		return // 无边框
	default:
		topLeft, topRight, bottomLeft, bottomRight = "╭", "╮", "╰", "╯"
		horizontal, vertical = "─", "│"
	}

	// 绘制上边框
	fmt.Printf("\033[1;1H%s", topLeft)
	for i := 0; i < width-2; i++ {
		fmt.Print(horizontal)
	}
	fmt.Print(topRight)

	// 绘制左右边框
	for i := 1; i < height-1; i++ {
		fmt.Printf("\033[%d;1H%s", i+1, vertical)
		fmt.Printf("\033[%d;%dH%s", i+1, width, vertical)
	}

	// 绘制下边框
	fmt.Printf("\033[%d;1H%s", height, bottomLeft)
	for i := 0; i < width-2; i++ {
		fmt.Print(horizontal)
	}
	fmt.Print(bottomRight)
}

// 显示文本
func displayText(x, y int, text, fgColor, bgColor string) {
    // 获取终端宽度
    termWidth, _, err := getTerminalSize()
    if err != nil {
        termWidth = 80
    }
    
    // 如果文本超出终端宽度，进行截断
    textWidth := getStringWidth(text)
    if x+textWidth > termWidth {
        // 计算可以显示的最大字符数
        maxWidth := termWidth - x
        truncated := ""
        currentWidth := 0
        
        for _, r := range text {
            rWidth := runewidth.RuneWidth(r)
            if currentWidth + rWidth > maxWidth {
                break
            }
            truncated += string(r)
            currentWidth += rWidth
        }
        
        text = truncated
    }
    
    // 设置颜色
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
		"transparent":  "",
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

// getInput 获取输入
func getInput() (string, error) {
    // 检查标准输入是否是终端设备
    if !term.IsTerminal(int(os.Stdin.Fd())) {
        // 如果不是终端设备，等待一段时间后返回空输入
        // 这样可以避免阻塞，同时允许程序继续运行
        time.Sleep(100 * time.Millisecond)
        return "", nil
    }

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
        case 72:
            return "home", nil
        case 70:
            return "end", nil
        case 53:
            if n >= 4 && buffer[3] == 126 {
                return "pageup", nil
            }
        case 54:
            if n >= 4 && buffer[3] == 126 {
                return "pagedown", nil
            }
        }
    } else if n == 1 {
        switch buffer[0] {
        case 32:
            return " ", nil
        case 9:
            return "tab", nil
        case 13:
            return "enter", nil
        case 27:
            return "esc", nil
        case 113:
            return "q", nil
        case 115:
            return "s", nil
        case 104:
            return "h", nil
        case 102:
            return "f", nil
        case 98:
            return "b", nil
        case 47:
            return "/", nil
        case 114:
            return "r", nil
        case 103:
            return "g", nil
        case 108:
            return "l", nil
        case 110:
            return "n", nil
        case 112:
            return "p", nil
        case 116:
            return "t", nil
        case 118:
            return "v", nil
        case 101:
            return "e", nil
        case 120:
            return "x", nil
        case 105: // i键
            return "i", nil
        }
    }

    return string(buffer[:n]), nil
}

// 文本换行处理
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

// 获取终端大小
func getTerminalSize() (int, int, error) {
	width, height, err := term.GetSize(int(os.Stdout.Fd()))
	if err != nil {
		return 80, 24, err
	}
	return width, height, nil
}

// 显示进度条
func displayProgressBar(x, y, width, current, total int, fgColor, bgColor string) {
	if total <= 0 {
		return
	}

	progress := float64(current) / float64(total)
	barWidth := width - 2 // 减去两端的括号
	fillWidth := int(float64(barWidth) * progress)

	bar := "["
	for i := 0; i < barWidth; i++ {
		if i < fillWidth {
			bar += "="
		} else if i == fillWidth {
			bar += ">"
		} else {
			bar += " "
		}
	}
	bar += "]"

	displayText(x, y, bar, fgColor, bgColor)
}

// showInputPrompt 显示输入提示
func showInputPrompt(prompt string) string {
    // 检查标准输入是否是终端设备
    if !term.IsTerminal(int(os.Stdin.Fd())) {
        // 如果不是终端设备，返回空字符串
        return ""
    }

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
    
    clearScreen()
    fmt.Print(prompt)
    
    reader := bufio.NewReader(os.Stdin)
    input, _ := reader.ReadString('\n')
    return strings.TrimSpace(input)
}

// hideWindow 隐藏窗口，显示真实的ls命令输出
func hideWindow() {
    isWindowHidden = true
    
    // 先恢复终端状态，以便正常显示命令输出
    if oldState != nil {
        term.Restore(int(os.Stdin.Fd()), oldState)
    }
    
    clearScreen()

    // 执行真实的ls命令
    var cmd *exec.Cmd
    if runtime.GOOS == "windows" {
        cmd = exec.Command("cmd", "/c", "dir", "%USERPROFILE%")
    } else {
        cmd = exec.Command("ls", "-la", os.Getenv("HOME"))
    }
    
    // 设置命令的输出和错误输出
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    
    // 执行命令
    err := cmd.Run()
    if err != nil {
        // 如果执行失败，使用假的输出作为后备
        fmt.Println("$ ls -la ~/")
        fmt.Println("total 120")
        fmt.Println("drwxr-xr-x  12 user  staff    384 Jan  1 12:00 .")
        fmt.Println("drwxr-xr-x   5 root  staff    160 Jan  1 12:00 ..")
        fmt.Println("-rw-r--r--   1 user  staff   3024 Jan  1 12:00 .bashrc")
        fmt.Println("-rw-r--r--   1 user  staff    220 Jan  1 12:00 .bash_logout")
        fmt.Println("drwxr-xr-x   3 user  staff     96 Jan  1 12:00 .config")
        fmt.Println("drwxr-xr-x   3 user  staff     96 Jan  1 12:00 Documents")
        fmt.Println("drwxr-xr-x   3 user  staff     96 Jan  1 12:00 Downloads")
        fmt.Println("drwxr-xr-x   3 user  staff     96 Jan  1 12:00 Music")
        fmt.Println("drwxr-xr-x   3 user  staff     96 Jan  1 12:00 Pictures")
        fmt.Println("drwxr-xr-x   3 user  staff     96 Jan  1 12:00 Videos")
        fmt.Println("drwxr-xr-x   3 user  staff     96 Jan  1 12:00 Projects")
    }
    
    // 显示命令提示符
    fmt.Print("$ ")
    
    // 重新设置原始模式，以便捕获按键
    if oldState != nil {
        term.MakeRaw(int(os.Stdin.Fd()))
    }
}

// showWindow 显示窗口
func showWindow() {
    isWindowHidden = false
    clearScreen()
}

// getStringWidth 获取字符串的显示宽度（考虑中文字符）
func getStringWidth(s string) int {
    width := 0
    for _, r := range s {
        width += runewidth.RuneWidth(r)
    }
    return width
}

// drawBottomStatusBar 绘制底部状态栏
func drawBottomStatusBar(style string, width, height int, progress, shortcuts string, fgColor, bgColor string) {
    // 计算状态栏位置
    barY := height - 3
    
    // 绘制上边框
    var horizontal, bottomLeft, bottomRight string
    switch style {
    case "round":
        bottomLeft, bottomRight = "╰", "╯"
        horizontal = "─"
    case "bold":
        bottomLeft, bottomRight = "┗", "┛"
        horizontal = "━"
    case "double":
        bottomLeft, bottomRight = "╚", "╝"
        horizontal = "═"
    case "thin":
        bottomLeft, bottomRight = "└", "┘"
        horizontal = "─"
    default:
        // 无边框模式，只显示文本
        if progress != "" {
            displayText(2, barY+1, progress, fgColor, bgColor)
        }
        if shortcuts != "" {
            // 截断过长的快捷键信息
            if len(shortcuts) > width-4 {
                shortcuts = shortcuts[:width-4]
            }
            displayText((width-len(shortcuts))/2, barY+1, shortcuts, fgColor, bgColor)
        }
        return
    }
    
    // 绘制底部边框
    fmt.Printf("\033[%d;1H%s", barY, bottomLeft)
    for i := 0; i < width-2; i++ {
        fmt.Print(horizontal)
    }
    fmt.Print(bottomRight)
    
    // 显示进度信息（左侧）
    if progress != "" {
        // 限制进度信息长度
        if len(progress) > (width/2)-2 {
            progress = progress[:(width/2)-2]
        }
        displayText(2, barY+1, progress, fgColor, bgColor)
    }
    
    // 显示快捷键信息（右侧）
    if shortcuts != "" {
        // 截断过长的快捷键信息
        if len(shortcuts) > (width/2)-2 {
            shortcuts = shortcuts[:(width/2)-2]
        }
        displayText(width-len(shortcuts)-2, barY+1, shortcuts, fgColor, bgColor)
    }
}

// getShortcutHint 获取简化的快捷键提示
func getShortcutHint() string {
    return "[←/→:翻页 s:设置 f:书签 /:搜索 r:朗读 q:退出]"
}