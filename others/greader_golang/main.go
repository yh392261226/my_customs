package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/gdamore/tcell/v2"
	"github.com/rivo/tview"
	"golang.org/x/text/encoding/charmap"
	"golang.org/x/text/encoding/simplifiedchinese"
	"golang.org/x/text/encoding/traditionalchinese"
	"golang.org/x/text/transform"
)

// 配置结构体
type Config struct {
	FontColor       string   `json:"font_color"`
	BackgroundColor string   `json:"background_color"`
	BorderColor     string   `json:"border_color"`
	BorderStyle     string   `json:"border_style"` // 边框样式
	FontSize        int      `json:"font_size"`
	MarginTop       int      `json:"margin_top"`
	MarginBottom    int      `json:"margin_bottom"`
	MarginLeft      int      `json:"margin_left"`
	MarginRight     int      `json:"margin_right"`
	PaddingTop      int      `json:"padding_top"`
	PaddingBottom   int      `json:"padding_bottom"`
	PaddingLeft     int      `json:"padding_left"`
	PaddingRight    int      `json:"padding_right"`
	Width           int      `json:"width"`
	Height          int      `json:"height"`
	HeightPercent   int      `json:"height_percent"`    // 屏幕高度百分比
	TransparentBg   bool     `json:"transparent_bg"`    // 透明背景
	UsePercent      bool     `json:"use_percent"`       // 使用百分比模式
	BookshelfPaths  []string `json:"bookshelf_paths"`   // 书架路径列表
	Theme           string   `json:"theme"`             // 主题：dark, light, blue, green, etc.
	AutoSave        bool     `json:"auto_save"`         // 自动保存进度
	LinesPerPage    int      `json:"lines_per_page"`    // 每页行数
	ShowProgressBar bool     `json:"show_progress_bar"` // 显示进度条
	EnableSounds    bool     `json:"enable_sounds"`     // 启用声音反馈
}

// 书签结构体
type Bookmark struct {
	FilePath string `json:"file_path"` // 文件路径
	Page     int    `json:"page"`
	Position int    `json:"position"`
	Note     string `json:"note"`
}

// 书籍结构体
type Book struct {
	FilePath string `json:"file_path"` // 文件路径
	Title    string `json:"title"`     // 书籍标题
	Progress int    `json:"progress"`  // 阅读进度（百分比）
	LastRead int64  `json:"last_read"` // 最后阅读时间（时间戳）
}

// 阅读器结构体
type NovelReader struct {
	app           *tview.Application
	pages         *tview.Pages
	contentView   *tview.TextView
	statusBar     *tview.TextView
	titleBar      *tview.TextView
	progressBar   *tview.TextView // 进度条
	flex          *tview.Flex     // 主布局
	config        Config
	bookmarks     []Bookmark
	books         []Book // 书架中的书籍
	content       []string
	currentPage   int
	totalPages    int
	fileName      string
	filePath      string
	width         int
	height        int
	configFile    string
	bookshelfFile string // 书架数据文件
	screen        tcell.Screen
	startTime     time.Time // 阅读开始时间
	charsRead     int       // 已读字符数
}

// 检测文件编码
func detectEncoding(content []byte) string {
	if utf8.Valid(content) {
		return "utf-8"
	}

	// 简略的编码检测逻辑
	if isGBK(content) {
		return "gbk"
	}
	if isBig5(content) {
		return "big5"
	}

	// 尝试常见中文编码
	if isCommonChinese(content) {
		return "gbk"
	}

	return "utf-8"
}

func isGBK(data []byte) bool {
	length := len(data)
	var i int = 0
	for i < length {
		if data[i] <= 0x7f {
			i++
			continue
		} else {
			if data[i] >= 0x81 && data[i] <= 0xfe && data[i+1] >= 0x40 && data[i+1] <= 0xfe && i+1 < length {
				i += 2
				continue
			} else {
				return false
			}
		}
	}
	return true
}

func isBig5(data []byte) bool {
	length := len(data)
	var i int = 0
	for i < length {
		if data[i] <= 0x7f {
			i++
			continue
		} else {
			if data[i] >= 0xa1 && data[i] <= 0xf9 &&
				((data[i+1] >= 0x40 && data[i+1] <= 0x7e) ||
					(data[i+1] >= 0xa1 && data[i+1] <= 0xfe)) &&
				i+1 < length {
				i += 2
				continue
			} else {
				return false
			}
		}
	}
	return true
}

// 新增函数：检测常见中文编码模式
func isCommonChinese(data []byte) bool {
	length := len(data)
	if length < 2 {
		return false
	}

	chineseCharCount := 0
	totalCharCount := 0

	for i := 0; i < length-1; i++ {
		if data[i] <= 0x7F {
			totalCharCount++
			continue
		}

		// 检查GBK汉字范围
		if data[i] >= 0x81 && data[i] <= 0xFE && data[i+1] >= 0x40 && data[i+1] <= 0xFE {
			chineseCharCount++
			totalCharCount += 2
			i++ // 跳过下一个字节
		}
	}

	// 如果中文字符占一定比例，认为是中文编码
	if totalCharCount > 0 && float64(chineseCharCount)/float64(totalCharCount) > 0.1 {
		return true
	}

	return false
}

// 转换编码到UTF-8
func convertToUTF8(content []byte, encoding string) (string, error) {
	var reader io.Reader = strings.NewReader(string(content))

	switch encoding {
	case "gbk", "gb2312":
		reader = transform.NewReader(reader, simplifiedchinese.GBK.NewDecoder())
	case "big5":
		reader = transform.NewReader(reader, traditionalchinese.Big5.NewDecoder())
	case "latin1", "iso-8859-1":
		reader = transform.NewReader(reader, charmap.ISO8859_1.NewDecoder())
	case "utf-8", "":
		// 已经是UTF-8或未指定，无需转换
		return string(content), nil
	default:
		return "", fmt.Errorf("unsupported encoding: %s", encoding)
	}

	decoded, err := io.ReadAll(reader)
	if err != nil {
		return "", err
	}

	return string(decoded), nil
}

// 初始化阅读器
func NewNovelReader() *NovelReader {
	// 获取配置文件的路径
	configDir, _ := os.UserHomeDir()
	configFile := filepath.Join(configDir, ".novel_reader_config.json")
	bookshelfFile := filepath.Join(configDir, ".novel_reader_bookshelf.json")

	nr := &NovelReader{
		app:           tview.NewApplication(),
		pages:         tview.NewPages(),
		contentView:   tview.NewTextView(),
		statusBar:     tview.NewTextView(),
		titleBar:      tview.NewTextView(),
		currentPage:   0,
		totalPages:    0,
		width:         80,
		height:        24,
		configFile:    configFile,
		bookshelfFile: bookshelfFile,
		config: Config{
			FontColor:       "white",
			BackgroundColor: "black",
			BorderColor:     "gray",
			BorderStyle:     "default",
			FontSize:        1,
			MarginTop:       1,
			MarginBottom:    1,
			MarginLeft:      2,
			MarginRight:     2,
			PaddingTop:      1,
			PaddingBottom:   1,
			PaddingLeft:     2,
			PaddingRight:    2,
			Width:           80,
			Height:          24,
			HeightPercent:   100,
			TransparentBg:   false,
			UsePercent:      false,
			BookshelfPaths:  []string{},
			Theme:           "dark",
			AutoSave:        true,
			LinesPerPage:    20,
			ShowProgressBar: true,
			EnableSounds:    false,
		},
	}

	// 加载配置
	nr.loadConfig()

	// 加载书签
	nr.loadBookmarks()

	// 加载书架
	nr.loadBookshelf()

	nr.setupUI()
	return nr
}

// 设置UI
func (nr *NovelReader) setupUI() {
	// 设置内容视图
	nr.contentView.
		SetDynamicColors(true).
		SetRegions(true).
		SetWordWrap(true).
		SetChangedFunc(func() {
			nr.app.Draw()
		})

	// 设置标题栏 - 美化样式
	nr.titleBar.
		SetDynamicColors(true).
		SetTextAlign(tview.AlignCenter).
		SetTextColor(tcell.ColorYellow).
		SetBackgroundColor(tcell.ColorDarkBlue)

	// 设置状态栏 - 美化样式
	nr.statusBar.
		SetDynamicColors(true).
		SetTextAlign(tview.AlignRight).
		SetTextColor(tcell.ColorLightGray).
		SetBackgroundColor(tcell.ColorDarkSlateGray)

	// 创建进度条
	nr.progressBar = tview.NewTextView()
	nr.progressBar.
		SetDynamicColors(true).
		SetTextAlign(tview.AlignCenter).
		SetTextColor(tcell.ColorGreen).
		SetBackgroundColor(tcell.ColorDarkSlateGray)

	// 创建主布局
	nr.flex = tview.NewFlex().
		SetDirection(tview.FlexRow).
		AddItem(nr.titleBar, 1, 0, false).
		AddItem(nr.contentView, 0, 1, true)

	// 根据配置决定是否显示进度条
	if nr.config.ShowProgressBar {
		nr.flex.AddItem(nr.progressBar, 1, 0, false)
	}

	nr.flex.AddItem(nr.statusBar, 1, 0, false)

	// 设置边框和边距
	nr.applyConfig()

	// 添加主页面
	nr.pages.AddPage("main", nr.flex, true, true)

	// 设置输入处理
	nr.setupInputHandlers()

	// 记录开始时间
	nr.startTime = time.Now()
}

// 应用配置
func (nr *NovelReader) applyConfig() {
	// 根据主题设置颜色
	nr.applyTheme()

	// 设置边框
	nr.contentView.SetBorder(true)
	nr.contentView.SetBorderColor(tcell.GetColor(nr.config.BorderColor))

	// 设置边框样式
	style := tcell.StyleDefault.
		Foreground(tcell.GetColor(nr.config.BorderColor)).
		Background(tcell.GetColor(nr.config.BackgroundColor))
	nr.contentView.SetBorderStyle(style)

	// 设置边距
	nr.contentView.SetBorderPadding(
		nr.config.PaddingTop,
		nr.config.PaddingBottom,
		nr.config.PaddingLeft,
		nr.config.PaddingRight)

	// 设置宽高
	if nr.config.UsePercent && nr.screen != nil {
		// 使用百分比模式
		_, screenHeight := nr.screen.Size()
		nr.height = int(float64(screenHeight) * float64(nr.config.HeightPercent) / 100.0)
	} else {
		// 使用固定宽高模式
		nr.width = nr.config.Width
		nr.height = nr.config.Height
	}

	// 更新布局
	nr.updateLayout()
}

// 应用主题
func (nr *NovelReader) applyTheme() {
	switch nr.config.Theme {
	case "light":
		nr.config.FontColor = "black"
		nr.config.BackgroundColor = "white"
		nr.config.BorderColor = "gray"
	case "blue":
		nr.config.FontColor = "white"
		nr.config.BackgroundColor = "darkblue"
		nr.config.BorderColor = "lightblue"
	case "green":
		nr.config.FontColor = "white"
		nr.config.BackgroundColor = "darkgreen"
		nr.config.BorderColor = "lightgreen"
	case "dark":
		fallthrough
	default:
		nr.config.FontColor = "white"
		nr.config.BackgroundColor = "black"
		nr.config.BorderColor = "gray"
	}

	// 设置颜色
	nr.contentView.SetTextColor(tcell.GetColor(nr.config.FontColor))

	// 设置背景颜色（支持透明背景）
	if nr.config.TransparentBg {
		nr.contentView.SetBackgroundColor(tcell.ColorDefault)
		nr.titleBar.SetBackgroundColor(tcell.ColorDefault)
		nr.statusBar.SetBackgroundColor(tcell.ColorDefault)
		if nr.progressBar != nil {
			nr.progressBar.SetBackgroundColor(tcell.ColorDefault)
		}
	} else {
		nr.contentView.SetBackgroundColor(tcell.GetColor(nr.config.BackgroundColor))
		nr.titleBar.SetBackgroundColor(tcell.GetColor(nr.config.BackgroundColor))
		nr.statusBar.SetBackgroundColor(tcell.GetColor(nr.config.BackgroundColor))
		if nr.progressBar != nil {
			nr.progressBar.SetBackgroundColor(tcell.GetColor(nr.config.BackgroundColor))
		}
	}
}

// 更新布局
func (nr *NovelReader) updateLayout() {
	// 清除现有布局
	nr.flex.Clear()

	// 重新添加组件
	nr.flex.AddItem(nr.titleBar, 1, 0, false)
	nr.flex.AddItem(nr.contentView, 0, 1, true)
	nr.flex.AddItem(nr.statusBar, 1, 0, false)
}

// 设置输入处理器
func (nr *NovelReader) setupInputHandlers() {
	nr.app.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
		switch event.Key() {
		case tcell.KeyRight, tcell.KeyCtrlN:
			nr.nextPage()
			return nil
		case tcell.KeyLeft, tcell.KeyCtrlP:
			nr.previousPage()
			return nil
		case tcell.KeyHome:
			nr.firstPage()
			return nil
		case tcell.KeyEnd:
			nr.lastPage()
			return nil
		case tcell.KeyRune:
			switch event.Rune() {
			case 'n': // 空格、f、n 都可以翻页
				nr.nextPage()
				return nil
			case 'p': // b、p 可以上一页
				nr.previousPage()
				return nil
			case 'q', 'Q':
				nr.saveProgress()
				nr.app.Stop()
				return nil
			case 'm', 'M': // 添加书签
				nr.addBookmark()
				return nil
			case 'l', 'L': // 查看书签列表
				nr.showBookmarks()
				return nil
			case 's', 'S': // 设置
				nr.showSettings()
				return nil
			case 'g', 'G': // 跳转页面
				nr.goToPage()
				return nil
			case '+':
				nr.changeFontSize(1)
				return nil
			case '-':
				nr.changeFontSize(-1)
				return nil
			case 'h', 'H', '?': // 显示帮助
				nr.showHelp()
				return nil
			case 'i', 'I': // 显示信息
				nr.showInfo()
				return nil
			case 'B', 'b': // 显示书架
				nr.showBookshelf()
				return nil
			case '/': // 搜索功能
				nr.fullTextSearch()
				return nil
			case 'f', 'F': // 全文搜索
				nr.fullTextSearch()
				return nil
			case 't', 'T': // 切换主题
				nr.toggleTheme()
				return nil
			case 'a', 'A': // 切换自动保存
				nr.config.AutoSave = !nr.config.AutoSave
				nr.saveConfig()
				status := "开启"
				if !nr.config.AutoSave {
					status = "关闭"
				}
				modal := tview.NewModal().
					SetText(fmt.Sprintf("自动保存已%s", status)).
					AddButtons([]string{"确定"}).
					SetDoneFunc(func(buttonIndex int, buttonLabel string) {
						nr.pages.SwitchToPage("main")
					})
				nr.pages.AddPage("auto_save_status", modal, true, true)
				return nil
			}
		}
		return event
	})
}

// 加载小说文件
func (nr *NovelReader) LoadNovel(filePath string) error {
	// 处理文件路径中的特殊字符
	absPath, err := filepath.Abs(filePath)
	if err != nil {
		return fmt.Errorf("failed to get absolute path: %v", err)
	}

	// 检查文件是否存在
	if _, err := os.Stat(absPath); os.IsNotExist(err) {
		return fmt.Errorf("file does not exist: %s", absPath)
	}

	// 读取文件内容
	content, err := os.ReadFile(absPath)
	if err != nil {
		return fmt.Errorf("failed to read file: %v", err)
	}

	// 检测编码
	encoding := detectEncoding(content)

	// 转换为UTF-8
	utf8Content, err := convertToUTF8(content, encoding)
	if err != nil {
		// 如果自动检测失败，尝试强制使用GBK
		fmt.Fprintf(os.Stderr, "Auto encoding failed, trying GBK...\n")
		utf8Content, err = convertToUTF8(content, "gbk")
		if err != nil {
			return fmt.Errorf("failed to convert to UTF-8: %v", err)
		}
	}

	// 检查转换后的内容是否为空
	if len(utf8Content) == 0 {
		fmt.Fprintf(os.Stderr, "Warning: Converted content is empty, trying raw content\n")
		// 尝试直接使用原始内容
		utf8Content = string(content)
	}

	// 保存文件名和路径
	nr.fileName = filepath.Base(absPath)
	nr.filePath = absPath

	// 处理内容 - 分割为页面
	nr.processContent(utf8Content)

	// 尝试加载阅读进度
	nr.loadProgress()

	// 更新书架中的书籍信息
	nr.updateBookInBookshelf(absPath)

	// 更新UI
	nr.updateUI()

	return nil
}

// 处理内容并分页
func (nr *NovelReader) processContent(content string) {
	// 清理内容：移除多余空行和空格
	cleanedContent := nr.cleanContent(content)

	// 按行分割，考虑配置中的每页行数
	lines := strings.Split(cleanedContent, "\n")

	// 计算每页可以显示多少行
	rowsPerPage := nr.height - nr.config.MarginTop - nr.config.MarginBottom -
		nr.config.PaddingTop - nr.config.PaddingBottom - 4 // 4 是标题和状态栏的高度

	// 如果配置了每页行数，使用配置值
	if nr.config.LinesPerPage > 0 {
		rowsPerPage = nr.config.LinesPerPage
	}

	if rowsPerPage <= 0 {
		rowsPerPage = 20 // 默认值
	}

	// 智能分页：避免在段落中间分页
	nr.content = nr.intelligentPaging(lines, rowsPerPage)

	nr.totalPages = len(nr.content)
	if nr.totalPages == 0 {
		nr.totalPages = 1
		nr.content = []string{"📖 文件内容为空或编码检测有误，请检查文件格式"}
	}
}

// 清理内容
func (nr *NovelReader) cleanContent(content string) string {
	// 移除BOM标记
	content = strings.TrimPrefix(content, "\ufeff")

	// 分割行并清理
	lines := strings.Split(content, "\n")
	var cleanedLines []string

	for _, line := range lines {
		// 移除行首行尾空格
		line = strings.TrimSpace(line)
		if line != "" {
			cleanedLines = append(cleanedLines, line)
		}
	}

	return strings.Join(cleanedLines, "\n")
}

// 智能分页：避免在段落中间分页
func (nr *NovelReader) intelligentPaging(lines []string, rowsPerPage int) []string {
	var pages []string
	var currentPage []string
	currentLineCount := 0

	for i := 0; i < len(lines); i++ {
		line := lines[i]

		// 如果是空行，可能是段落分隔
		if strings.TrimSpace(line) == "" {
			// 如果当前页还有空间，继续添加
			if currentLineCount < rowsPerPage {
				currentPage = append(currentPage, line)
				currentLineCount++
			} else {
				// 当前页已满，开始新页
				if len(currentPage) > 0 {
					pages = append(pages, strings.Join(currentPage, "\n"))
				}
				currentPage = []string{line}
				currentLineCount = 1
			}
			continue
		}

		// 检查是否是段落开始（前面有空行）
		isParagraphStart := i > 0 && strings.TrimSpace(lines[i-1]) == ""

		// 如果是段落开始且当前页接近满，开始新页
		if isParagraphStart && currentLineCount > rowsPerPage-5 && currentLineCount > 0 {
			pages = append(pages, strings.Join(currentPage, "\n"))
			currentPage = []string{line}
			currentLineCount = 1
		} else if currentLineCount >= rowsPerPage {
			// 当前页已满，开始新页
			pages = append(pages, strings.Join(currentPage, "\n"))
			currentPage = []string{line}
			currentLineCount = 1
		} else {
			// 添加到当前页
			currentPage = append(currentPage, line)
			currentLineCount++
		}
	}

	// 添加最后一页
	if len(currentPage) > 0 {
		pages = append(pages, strings.Join(currentPage, "\n"))
	}

	return pages
}

// 更新UI显示
func (nr *NovelReader) updateUI() {
	// 设置标题 - 美化样式
	title := fmt.Sprintf("[yellow]📖 %s[-] - 📄 第 %d/%d 页", nr.fileName, nr.currentPage+1, nr.totalPages)
	nr.titleBar.SetText(title)

	// 显示当前页内容
	if nr.currentPage < len(nr.content) {
		nr.contentView.SetText(nr.content[nr.currentPage])
	} else if len(nr.content) > 0 {
		// 如果当前页码超出范围，显示第一页
		nr.currentPage = 0
		nr.contentView.SetText(nr.content[0])
	}

	// 计算阅读进度
	progressPercent := float64(nr.currentPage+1) / float64(nr.totalPages) * 100

	// 更新进度条
	if nr.config.ShowProgressBar {
		progressBar := nr.createProgressBar(progressPercent)
		nr.progressBar.SetText(progressBar)
	}

	// 更新状态栏 - 美化样式
	progress := fmt.Sprintf("📊 进度: %d/%d (%.1f%%)",
		nr.currentPage+1, nr.totalPages, progressPercent)

	// 更详细的帮助信息
	helpText := fmt.Sprintf("[lightgray]%s | 🚪Q:退出 | ⬅️➡️/空格:翻页 | 📑M:书签 | 📚L:列表 | ⚙️S:设置 | 🔍G:跳转 | ➕➖:字号 | ❓H:帮助 | 📖B:书架 | 🔍/:搜索 | 🎨T:主题[-]", progress)
	nr.statusBar.SetText(helpText)

	// 自动保存进度
	if nr.config.AutoSave {
		nr.saveProgress()
	}
}

// 下一页
func (nr *NovelReader) nextPage() {
	if nr.currentPage < nr.totalPages-1 {
		nr.currentPage++
		nr.updateUI()
	}
}

// 上一页
func (nr *NovelReader) previousPage() {
	if nr.currentPage > 0 {
		nr.currentPage--
		nr.updateUI()
	}
}

// 第一页
func (nr *NovelReader) firstPage() {
	nr.currentPage = 0
	nr.updateUI()
}

// 最后一页
func (nr *NovelReader) lastPage() {
	nr.currentPage = nr.totalPages - 1
	nr.updateUI()
}

// 跳转到指定页
func (nr *NovelReader) goToPage() {
	// 创建一个模态对话框用于输入页码
	modal := tview.NewModal().
		SetText("Enter page number:").
		AddButtons([]string{"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Cancel"}).
		SetDoneFunc(func(buttonIndex int, buttonLabel string) {
			if buttonLabel != "Cancel" {
				if pageNum, err := strconv.Atoi(buttonLabel); err == nil {
					if pageNum > 0 && pageNum <= nr.totalPages {
						nr.currentPage = pageNum - 1
						nr.updateUI()
					}
				}
			}
			nr.pages.SwitchToPage("main")
		})

	modal.SetBorder(true).SetTitle("Go to Page")
	nr.pages.AddPage("goto", modal, true, true)
}

// 添加书签
func (nr *NovelReader) addBookmark() {
	bookmark := Bookmark{
		FilePath: nr.filePath,
		Page:     nr.currentPage,
		Position: 0,
		Note:     fmt.Sprintf("Page %d", nr.currentPage+1),
	}

	nr.bookmarks = append(nr.bookmarks, bookmark)

	// 保存书签
	nr.saveBookmarks()

	// 显示提示信息
	modal := tview.NewModal().
		SetText("Bookmark added").
		AddButtons([]string{"OK"}).
		SetDoneFunc(func(buttonIndex int, buttonLabel string) {
			nr.pages.SwitchToPage("main")
		})

	nr.pages.AddPage("bookmark_added", modal, true, true)
}

// 显示书签列表
func (nr *NovelReader) showBookmarks() {
	list := tview.NewList().
		AddItem("Back", "Return to reading", 'q', func() {
			nr.pages.SwitchToPage("main")
		}).
		AddItem("Add new bookmark", "Add current file to bookmarks", 'a', func() {
			nr.addBookmark()
		})

	// 添加书签项
	for i, bookmark := range nr.bookmarks {
		// 创建闭包内的局部变量
		bm := bookmark
		index := i

		// 获取文件名
		fileName := filepath.Base(bm.FilePath)

		list.AddItem(
			fmt.Sprintf("%s - Page %d: %s", fileName, bm.Page+1, bm.Note),
			fmt.Sprintf("Path: %s", bm.FilePath),
			0,
			func() {
				// 加载书签对应的文件
				if err := nr.LoadNovel(bm.FilePath); err != nil {
					// 显示错误信息
					modal := tview.NewModal().
						SetText(fmt.Sprintf("Error loading file: %v", err)).
						AddButtons([]string{"OK"}).
						SetDoneFunc(func(buttonIndex int, buttonLabel string) {
							nr.pages.SwitchToPage("bookmarks")
						})
					nr.pages.AddPage("load_error", modal, true, true)
				} else {
					// 跳转到书签位置
					nr.currentPage = bm.Page
					nr.updateUI()
					nr.pages.SwitchToPage("main")
				}
			}).
			AddItem("Delete this bookmark", "", 'd', func() {
				// 删除书签
				if index < len(nr.bookmarks) {
					nr.bookmarks = append(nr.bookmarks[:index], nr.bookmarks[index+1:]...)
					// 保存书签
					nr.saveBookmarks()
					// 重新显示书签列表
					nr.showBookmarks()
				}
			})
	}

	list.SetBorder(true).SetTitle("Bookmarks")
	nr.pages.AddPage("bookmarks", list, true, true)
}

// 显示设置界面
func (nr *NovelReader) showSettings() {
	form := tview.NewForm()

	// 添加主题选项
	form.AddDropDown("Theme", []string{"dark", "light", "blue", "green"},
		getIndex(nr.config.Theme, []string{"dark", "light", "blue", "green"}),
		func(option string, index int) {
			nr.config.Theme = option
			nr.applyConfig()
		})

	// 添加设置选项
	form.AddDropDown("Font color", []string{"white", "black", "red", "green", "blue", "yellow", "cyan", "magenta"},
		getIndex(nr.config.FontColor, []string{"white", "black", "red", "green", "blue", "yellow", "cyan", "magenta"}),
		func(option string, index int) {
			nr.config.FontColor = option
			nr.applyConfig()
		})

	form.AddDropDown("Background color", []string{"black", "white", "red", "green", "blue", "yellow", "cyan", "magenta", "default"},
		getIndex(nr.config.BackgroundColor, []string{"black", "white", "red", "green", "blue", "yellow", "cyan", "magenta", "default"}),
		func(option string, index int) {
			nr.config.BackgroundColor = option
			nr.applyConfig()
		})

	form.AddDropDown("Border color", []string{"gray", "white", "black", "red", "green", "blue", "yellow", "cyan", "magenta"},
		getIndex(nr.config.BorderColor, []string{"gray", "white", "black", "red", "green", "blue", "yellow", "cyan", "magenta"}),
		func(option string, index int) {
			nr.config.BorderColor = option
			nr.applyConfig()
		})

	// 添加边框样式选项
	form.AddDropDown("Border style", []string{"default", "rounded", "double", "thin", "bold"},
		getIndex(nr.config.BorderStyle, []string{"default", "rounded", "double", "thin", "bold"}),
		func(option string, index int) {
			nr.config.BorderStyle = option
			nr.applyConfig()
		})

	// 添加透明背景选项
	form.AddCheckbox("Transparent background", nr.config.TransparentBg, func(checked bool) {
		nr.config.TransparentBg = checked
		nr.applyConfig()
	})

	// 添加显示模式选项
	form.AddCheckbox("Use percentage mode", nr.config.UsePercent, func(checked bool) {
		nr.config.UsePercent = checked
		nr.applyConfig()
	})

	// 添加高度百分比设置
	form.AddInputField("Height percentage", strconv.Itoa(nr.config.HeightPercent), 3, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil && val > 0 && val <= 100 {
			nr.config.HeightPercent = val
			nr.applyConfig()
		}
	})

	// 添加边距和填充设置
	form.AddInputField("Margin Top", strconv.Itoa(nr.config.MarginTop), 2, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil {
			nr.config.MarginTop = val
		}
	})

	form.AddInputField("Margin Bottom", strconv.Itoa(nr.config.MarginBottom), 2, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil {
			nr.config.MarginBottom = val
		}
	})

	form.AddInputField("Margin Left", strconv.Itoa(nr.config.MarginLeft), 2, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil {
			nr.config.MarginLeft = val
		}
	})

	form.AddInputField("Margin Right", strconv.Itoa(nr.config.MarginRight), 2, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil {
			nr.config.MarginRight = val
		}
	})

	form.AddInputField("Padding Top", strconv.Itoa(nr.config.PaddingTop), 2, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil {
			nr.config.PaddingTop = val
		}
	})

	form.AddInputField("Padding Bottom", strconv.Itoa(nr.config.PaddingBottom), 2, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil {
			nr.config.PaddingBottom = val
		}
	})

	form.AddInputField("Padding Left", strconv.Itoa(nr.config.PaddingLeft), 2, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil {
			nr.config.PaddingLeft = val
		}
	})

	form.AddInputField("Padding Right", strconv.Itoa(nr.config.PaddingRight), 2, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil {
			nr.config.PaddingRight = val
		}
	})

	// 添加宽度和高度设置
	form.AddInputField("Width", strconv.Itoa(nr.config.Width), 3, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil && val > 0 {
			nr.config.Width = val
			nr.applyConfig()
		}
	})

	form.AddInputField("Height", strconv.Itoa(nr.config.Height), 3, nil, func(text string) {
		if val, err := strconv.Atoi(text); err == nil && val > 0 {
			nr.config.Height = val
			nr.applyConfig()
		}
	})

	// 添加书架路径设置
	form.AddInputField("Bookshelf Paths (comma separated)", strings.Join(nr.config.BookshelfPaths, ","), 50, nil, func(text string) {
		paths := strings.Split(text, ",")
		// 清理路径
		for i, path := range paths {
			paths[i] = strings.TrimSpace(path)
		}
		nr.config.BookshelfPaths = paths
	})

	form.AddButton("Save", func() {
		nr.saveConfig()
		// 重新处理内容以适应新的设置
		if nr.filePath != "" {
			content, err := os.ReadFile(nr.filePath)
			if err == nil {
				encoding := detectEncoding(content)
				utf8Content, err := convertToUTF8(content, encoding)
				if err == nil {
					nr.processContent(utf8Content)
					nr.updateUI()
				}
			}
		}
		nr.pages.SwitchToPage("main")
	})

	form.AddButton("Cancel", func() {
		nr.pages.SwitchToPage("main")
	})

	form.AddButton("Show Config Path", func() {
		modal := tview.NewModal().
			SetText(fmt.Sprintf("Config file location:\n%s", nr.configFile)).
			AddButtons([]string{"OK"}).
			SetDoneFunc(func(buttonIndex int, buttonLabel string) {
				nr.pages.SwitchToPage("settings")
			})
		modal.SetBorder(true).SetTitle("Config File Location")
		nr.pages.AddPage("config_path", modal, true, true)
	})

	form.SetBorder(true).SetTitle("Reader Settings")
	nr.pages.AddPage("settings", form, true, true)
}

// 获取选项在列表中的索引
func getIndex(value string, options []string) int {
	for i, option := range options {
		if option == value {
			return i
		}
	}
	return 0
}

// 显示帮助信息
func (nr *NovelReader) showHelp() {
	helpText := `
[::b]📖 终端小说阅读器 帮助[::-]

[::b]📋 基本导航:[-]
  🚪 Q - 退出阅读器
  ⬅️  ➡️ / 空格 - 翻页
  🔠 N/P - 下一页/上一页
  🏠 Home - 第一页
  🏁 End - 最后一页
  🔍 G - 跳转到指定页

[::b]📑 书签功能:[-]
  📑 M - 添加书签
  📚 L - 查看书签列表

[::b]📖 书架管理:[-]
  📖 B - 显示书架
  🔄 S - 扫描书架路径

[::b]🔍 搜索功能:[-]
  / - 快速搜索
  🔍 F - 全文搜索

[::b]⚙️ 设置选项:[-]
  ⚙️ S - 打开设置
  ➕ ➖ - 调整字体大小
  🎨 T - 切换主题

[::b]ℹ️ 其他功能:[-]
  ❓ H/? - 显示帮助
  ℹ️ I - 显示阅读器信息
  💾 A - 自动保存开关

按任意键返回阅读。
`

	modal := tview.NewModal().
		SetText(helpText).
		AddButtons([]string{"确定"}).
		SetDoneFunc(func(buttonIndex int, buttonLabel string) {
			nr.pages.SwitchToPage("main")
		})

	modal.SetBorder(true).SetTitle("📖 帮助信息")
	nr.pages.AddPage("help", modal, true, true)
}

// 显示阅读器信息
func (nr *NovelReader) showInfo() {
	infoText := fmt.Sprintf(`
[::b]Novel Reader Information[::-]

[::b]File:[-] %s
[::b]Current Page:[-] %d/%d
[::b]Config File:[-] %s
[::b]Bookshelf File:[-] %s
[::b]Terminal Size:[-] %dx%d
[::b]Content Size:[-] %dx%d (with margins)

[::b]Current Settings:[-]
  Font Color: %s
  Background Color: %s
  Border Color: %s
  Border Style: %s
  Transparent Background: %v
  Height Percentage: %d%%
  Use Percentage Mode: %v
  Margins: T:%d B:%d L:%d R:%d
  Padding: T:%d B:%d L:%d R:%d

Press any key to return.
`,
		nr.fileName,
		nr.currentPage+1, nr.totalPages,
		nr.configFile,
		nr.bookshelfFile,
		nr.width, nr.height,
		nr.width-nr.config.MarginLeft-nr.config.MarginRight,
		nr.height-nr.config.MarginTop-nr.config.MarginBottom,
		nr.config.FontColor,
		nr.config.BackgroundColor,
		nr.config.BorderColor,
		nr.config.BorderStyle,
		nr.config.TransparentBg,
		nr.config.HeightPercent,
		nr.config.UsePercent,
		nr.config.MarginTop, nr.config.MarginBottom, nr.config.MarginLeft, nr.config.MarginRight,
		nr.config.PaddingTop, nr.config.PaddingBottom, nr.config.PaddingLeft, nr.config.PaddingRight)

	modal := tview.NewModal().
		SetText(infoText).
		AddButtons([]string{"OK"}).
		SetDoneFunc(func(buttonIndex int, buttonLabel string) {
			nr.pages.SwitchToPage("main")
		})

	modal.SetBorder(true).SetTitle("Reader Information")
	nr.pages.AddPage("info", modal, true, true)
}

// 改变字体大小
func (nr *NovelReader) changeFontSize(delta int) {
	// 在终端中，我们无法真正改变字体大小
	// 但可以通过调整每页显示的行数来模拟
	if delta > 0 {
		nr.height -= 2 // 减少高度，显示更少行
	} else {
		nr.height += 2 // 增加高度，显示更多行
	}

	if nr.height < 10 {
		nr.height = 10
	}

	// 重新处理内容
	if nr.filePath != "" {
		content, err := os.ReadFile(nr.filePath)
		if err == nil {
			encoding := detectEncoding(content)
			utf8Content, err := convertToUTF8(content, encoding)
			if err == nil {
				// 保存当前页面
				currentPage := nr.currentPage
				// 重新处理内容
				nr.processContent(utf8Content)
				// 恢复当前页面（如果可能）
				if currentPage < nr.totalPages {
					nr.currentPage = currentPage
				} else {
					nr.currentPage = nr.totalPages - 1
				}
				nr.updateUI()
			}
		}
	}
}

// 创建进度条
func (nr *NovelReader) createProgressBar(percent float64) string {
	const barWidth = 20
	filled := int(percent / 100 * barWidth)
	empty := barWidth - filled

	// 使用Unicode字符创建更美观的进度条
	filledChar := "█"
	emptyChar := "░"

	bar := strings.Repeat(filledChar, filled) + strings.Repeat(emptyChar, empty)
	return fmt.Sprintf("[green]%s[-] %.1f%%", bar, percent)
}

// 加载阅读进度
func (nr *NovelReader) loadProgress() {
	// 从文件加载进度
	progressFile := nr.filePath + ".progress"
	if _, err := os.Stat(progressFile); err == nil {
		data, err := os.ReadFile(progressFile)
		if err == nil {
			if page, err := strconv.Atoi(string(data)); err == nil {
				if page < nr.totalPages {
					nr.currentPage = page
				}
			}
		}
	}
}

// 保存阅读进度
func (nr *NovelReader) saveProgress() {
	// 保存进度到文件
	progressFile := nr.filePath + ".progress"
	_ = os.WriteFile(progressFile, []byte(strconv.Itoa(nr.currentPage)), 0644)
}

// 保存配置
func (nr *NovelReader) saveConfig() {
	data, _ := json.MarshalIndent(nr.config, "", "  ")
	_ = os.WriteFile(nr.configFile, data, 0644)
}

// 加载配置
func (nr *NovelReader) loadConfig() {
	if _, err := os.Stat(nr.configFile); err == nil {
		data, err := os.ReadFile(nr.configFile)
		if err == nil {
			_ = json.Unmarshal(data, &nr.config)
		}
	}
}

// 保存书签
func (nr *NovelReader) saveBookmarks() {
	bookmarkFile := filepath.Join(filepath.Dir(nr.configFile), ".novel_reader_bookmarks.json")
	data, _ := json.MarshalIndent(nr.bookmarks, "", "  ")
	_ = os.WriteFile(bookmarkFile, data, 0644)
}

// 加载书签
func (nr *NovelReader) loadBookmarks() {
	bookmarkFile := filepath.Join(filepath.Dir(nr.configFile), ".novel_reader_bookmarks.json")
	if _, err := os.Stat(bookmarkFile); err == nil {
		data, err := os.ReadFile(bookmarkFile)
		if err == nil {
			_ = json.Unmarshal(data, &nr.bookmarks)
		}
	}
}

// 加载书架
func (nr *NovelReader) loadBookshelf() {
	if _, err := os.Stat(nr.bookshelfFile); err == nil {
		data, err := os.ReadFile(nr.bookshelfFile)
		if err == nil {
			_ = json.Unmarshal(data, &nr.books)
		}
	}
}

// 保存书架
func (nr *NovelReader) saveBookshelf() {
	data, _ := json.MarshalIndent(nr.books, "", "  ")
	_ = os.WriteFile(nr.bookshelfFile, data, 0644)
}

// 扫描书架路径中的小说文件
func (nr *NovelReader) scanBookshelfPaths() {
	nr.books = []Book{} // 清空当前书籍列表

	for _, path := range nr.config.BookshelfPaths {
		// 检查路径是否存在
		if _, err := os.Stat(path); os.IsNotExist(err) {
			continue
		}

		// 扫描路径中的文本文件
		filepath.Walk(path, func(filePath string, info os.FileInfo, err error) error {
			if err != nil {
				return nil
			}

			// 只处理文件，跳过目录
			if info.IsDir() {
				return nil
			}

			// 检查文件扩展名
			ext := strings.ToLower(filepath.Ext(filePath))
			if ext == ".txt" || ext == ".md" {
				// 检查是否已经在书籍列表中
				found := false
				for _, book := range nr.books {
					if book.FilePath == filePath {
						found = true
						break
					}
				}

				if !found {
					// 添加到书籍列表
					book := Book{
						FilePath: filePath,
						Title:    strings.TrimSuffix(info.Name(), ext),
						Progress: 0,
						LastRead: 0,
					}
					nr.books = append(nr.books, book)
				}
			}

			return nil
		})
	}

	// 保存书架
	nr.saveBookshelf()
}

// 更新书架中的书籍信息
func (nr *NovelReader) updateBookInBookshelf(filePath string) {
	for i, book := range nr.books {
		if book.FilePath == filePath {
			// 更新阅读进度和最后阅读时间
			nr.books[i].Progress = int(float64(nr.currentPage+1) / float64(nr.totalPages) * 100)
			nr.books[i].LastRead = getCurrentTimestamp()
			nr.saveBookshelf()
			return
		}
	}

	// 如果书籍不在书架中，添加它
	book := Book{
		FilePath: filePath,
		Title:    strings.TrimSuffix(filepath.Base(filePath), filepath.Ext(filePath)),
		Progress: int(float64(nr.currentPage+1) / float64(nr.totalPages) * 100),
		LastRead: getCurrentTimestamp(),
	}
	nr.books = append(nr.books, book)
	nr.saveBookshelf()
}

// 获取当前时间戳
func getCurrentTimestamp() int64 {
	return int64(time.Now().Unix())
}

// 搜索功能
func (nr *NovelReader) showSearch() {
	// 创建搜索对话框
	modal := tview.NewModal().
		SetText("输入搜索关键词:").
		AddButtons([]string{"搜索", "取消"}).
		SetDoneFunc(func(buttonIndex int, buttonLabel string) {
			if buttonLabel == "搜索" {
				nr.performSearch("关键词") // 这里需要实现实际的搜索逻辑
			}
			nr.pages.SwitchToPage("main")
		})

	modal.SetBorder(true).SetTitle("搜索")
	nr.pages.AddPage("search", modal, true, true)
}

// 全文搜索功能
func (nr *NovelReader) fullTextSearch() {
	// 创建输入框用于搜索
	inputField := tview.NewInputField().
		SetLabel("搜索关键词: ").
		SetFieldWidth(30)

	inputField.SetDoneFunc(func(key tcell.Key) {
		if key == tcell.KeyEnter {
			searchTerm := inputField.GetText()
			if searchTerm != "" {
				nr.performSearch(searchTerm)
			}
		} else if key == tcell.KeyEsc {
			nr.pages.SwitchToPage("main")
		}
	})

	form := tview.NewForm().
		AddFormItem(inputField).
		AddButton("搜索", func() {
			searchTerm := inputField.GetText()
			if searchTerm != "" {
				nr.performSearch(searchTerm)
			}
		}).
		AddButton("取消", func() {
			nr.pages.SwitchToPage("main")
		})

	form.SetBorder(true).SetTitle("全文搜索")
	nr.pages.AddPage("full_search", form, true, true)
}

// 执行搜索
func (nr *NovelReader) performSearch(searchTerm string) {
	var results []struct {
		page    int
		line    int
		content string
	}

	// 在所有页面中搜索
	for pageNum, pageContent := range nr.content {
		lines := strings.Split(pageContent, "\n")
		for lineNum, line := range lines {
			if strings.Contains(strings.ToLower(line), strings.ToLower(searchTerm)) {
				// 截取匹配内容的前后文
				start := max(0, lineNum-2)
				end := min(len(lines), lineNum+3)
				context := strings.Join(lines[start:end], "\n")

				results = append(results, struct {
					page    int
					line    int
					content string
				}{
					page:    pageNum,
					line:    lineNum,
					content: context,
				})
			}
		}
	}

	// 显示搜索结果
	if len(results) > 0 {
		nr.showSearchResults(searchTerm, results)
	} else {
		modal := tview.NewModal().
			SetText(fmt.Sprintf("未找到包含 \"%s\" 的内容", searchTerm)).
			AddButtons([]string{"确定"}).
			SetDoneFunc(func(buttonIndex int, buttonLabel string) {
				nr.pages.SwitchToPage("main")
			})
		nr.pages.AddPage("no_results", modal, true, true)
	}
}

// 显示搜索结果
func (nr *NovelReader) showSearchResults(searchTerm string, results []struct {
	page    int
	line    int
	content string
}) {
	list := tview.NewList().
		AddItem("返回", "返回阅读", 'b', func() {
			nr.pages.SwitchToPage("main")
		})

	for _, result := range results {
		result := result // 创建局部变量
		list.AddItem(
			fmt.Sprintf("第 %d 页, 第 %d 行", result.page+1, result.line+1),
			fmt.Sprintf("...%s...", truncateString(result.content, 50)),
			0,
			func() {
				// 跳转到搜索结果位置
				nr.currentPage = result.page
				nr.updateUI()
				nr.pages.SwitchToPage("main")
			})
	}

	list.SetBorder(true).SetTitle(fmt.Sprintf("搜索结果: \"%s\" (%d 个匹配)", searchTerm, len(results)))
	nr.pages.AddPage("search_results", list, true, true)
}

// 切换主题功能
func (nr *NovelReader) toggleTheme() {
	themes := []string{"dark", "light", "blue", "green"}
	currentIndex := getIndex(nr.config.Theme, themes)
	nextIndex := (currentIndex + 1) % len(themes)
	nr.config.Theme = themes[nextIndex]
	nr.applyConfig()

	// 显示主题切换提示
	modal := tview.NewModal().
		SetText(fmt.Sprintf("已切换到 %s 主题", nr.config.Theme)).
		AddButtons([]string{"确定"}).
		SetDoneFunc(func(buttonIndex int, buttonLabel string) {
			nr.pages.SwitchToPage("main")
		})
	nr.pages.AddPage("theme_changed", modal, true, true)
}

// 辅助函数
func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func truncateString(s string, maxLength int) string {
	if len(s) <= maxLength {
		return s
	}
	return s[:maxLength-3] + "..."
}

// 显示书架界面
func (nr *NovelReader) showBookshelf() {
	list := tview.NewList().
		AddItem("Back", "Return to reading", 'q', func() {
			nr.pages.SwitchToPage("main")
		}).
		AddItem("Scan Bookshelf", "Scan bookshelf paths for new books", 's', func() {
			nr.scanBookshelfPaths()
			nr.showBookshelf() // 刷新书架
		}).
		AddItem("Add Bookshelf Path", "Add a new path to bookshelf", 'a', func() {
			nr.showAddBookshelfPath()
		})

	// 按最后阅读时间排序书籍（最近阅读的在前）
	sort.Slice(nr.books, func(i, j int) bool {
		return nr.books[i].LastRead > nr.books[j].LastRead
	})

	// 添加书籍项
	for i, book := range nr.books {
		// 创建闭包内的局部变量
		b := book
		index := i

		// 格式化最后阅读时间
		lastRead := "Never read"
		if b.LastRead > 0 {
			lastRead = time.Unix(b.LastRead, 0).Format("2006-01-02 15:04")
		}

		list.AddItem(
			fmt.Sprintf("%s (%d%%)", b.Title, b.Progress),
			fmt.Sprintf("Path: %s | Last read: %s", b.FilePath, lastRead),
			0,
			func() {
				// 加载书籍
				if err := nr.LoadNovel(b.FilePath); err != nil {
					// 显示错误信息
					modal := tview.NewModal().
						SetText(fmt.Sprintf("Error loading book: %v", err)).
						AddButtons([]string{"OK"}).
						SetDoneFunc(func(buttonIndex int, buttonLabel string) {
							nr.pages.SwitchToPage("bookshelf")
						})
					nr.pages.AddPage("load_error", modal, true, true)
				} else {
					nr.pages.SwitchToPage("main")
				}
			}).
			AddItem("Remove from Bookshelf", "", 'd', func() {
				// 从书架中删除书籍
				if index < len(nr.books) {
					nr.books = append(nr.books[:index], nr.books[index+1:]...)
					// 保存书架
					nr.saveBookshelf()
					// 重新显示书架
					nr.showBookshelf()
				}
			})
	}

	list.SetBorder(true).SetTitle("Bookshelf")
	nr.pages.AddPage("bookshelf", list, true, true)
}

// 显示添加书架路径界面
func (nr *NovelReader) showAddBookshelfPath() {
	// 保存原来的输入处理器
	originalInputHandler := nr.app.GetInputCapture()

	// 创建表单
	form := tview.NewForm()

	// 添加输入字段
	pathInput := tview.NewInputField().SetLabel("Path").SetFieldWidth(50)
	form.AddFormItem(pathInput)

	// 完全禁用应用程序级别的输入处理
	nr.app.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
		// 只允许ESC键用于返回
		if event.Key() == tcell.KeyEsc {
			// 恢复输入处理器
			nr.app.SetInputCapture(originalInputHandler)
			nr.showBookshelf()
			return nil
		}

		// 允许所有其他按键事件传递给表单处理
		return event
	})

	// 设置表单的输入处理
	form.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
		// 允许ESC键返回
		if event.Key() == tcell.KeyEsc {
			// 恢复输入处理器
			nr.app.SetInputCapture(originalInputHandler)
			nr.showBookshelf()
			return nil
		}

		// 允许所有其他按键
		return event
	})

	// 添加"Add"按钮
	form.AddButton("Add", func() {
		// 获取输入框的值
		path := pathInput.GetText()

		if path != "" {
			// 检查路径是否存在
			if _, err := os.Stat(path); os.IsNotExist(err) {
				// 显示错误信息
				modal := tview.NewModal().
					SetText(fmt.Sprintf("Path does not exist: %s", path)).
					AddButtons([]string{"OK"}).
					SetDoneFunc(func(buttonIndex int, buttonLabel string) {
						// 保持当前输入处理器不变
						nr.pages.SwitchToPage("add_bookshelf_path")
					})
				nr.pages.AddPage("path_error", modal, true, true)
				return
			}

			// 添加到书架路径
			nr.config.BookshelfPaths = append(nr.config.BookshelfPaths, path)
			// 保存配置
			nr.saveConfig()
			// 扫描新路径
			nr.scanBookshelfPaths()
			// 恢复输入处理器
			nr.app.SetInputCapture(originalInputHandler)
			// 返回书架
			nr.showBookshelf()
		}
	})

	// 添加"Cancel"按钮
	form.AddButton("Cancel", func() {
		// 恢复输入处理器
		nr.app.SetInputCapture(originalInputHandler)
		nr.showBookshelf()
	})

	form.SetBorder(true).SetTitle("Add Bookshelf Path")
	nr.pages.AddPage("add_bookshelf_path", form, true, true)

	// 手动跟踪页面变化而不是使用 GetChangedFunc
	currentPage, _ := nr.pages.GetFrontPage()
	go func() {
		for {
			time.Sleep(100 * time.Millisecond)
			newPage, _ := nr.pages.GetFrontPage()
			if newPage != currentPage && newPage != "add_bookshelf_path" {
				// 如果离开了添加书架路径页面，恢复输入处理器
				nr.app.SetInputCapture(originalInputHandler)
				break
			}
			currentPage = newPage
		}
	}()

	// 设置表单焦点
	nr.app.SetFocus(form)
}

// 运行阅读器
func (nr *NovelReader) Run() error {
	// 获取屏幕对象
	screen, err := tcell.NewScreen()
	if err != nil {
		return err
	}
	nr.screen = screen

	// 应用配置（设置高度百分比）
	nr.applyConfig()

	return nr.app.SetRoot(nr.pages, true).SetScreen(screen).Run()
}

// 非交互模式显示
func (nr *NovelReader) DisplayPage(pageNum int) {
	if pageNum >= 0 && pageNum < nr.totalPages {
		nr.currentPage = pageNum
	}

	nr.updateUI()

	// 直接显示内容而不进入事件循环
	fmt.Println(nr.contentView.GetText(false))
}

// 显示书签选择界面（当没有文件传入时）
func (nr *NovelReader) showBookmarkSelection() {
	// 如果没有书签，显示提示信息
	if len(nr.bookmarks) == 0 {
		modal := tview.NewModal().
			SetText("No bookmarks available. Please open a file first to create bookmarks.").
			AddButtons([]string{"OK"}).
			SetDoneFunc(func(buttonIndex int, buttonLabel string) {
				nr.app.Stop()
			})
		modal.SetBorder(true).SetTitle("No Bookmarks")
		nr.pages.AddPage("no_bookmarks", modal, true, true)
		return
	}

	// 显示书签列表
	nr.showBookmarks()
}

func main() {
	reader := NewNovelReader()

	// 检查是否有文件参数传入
	if len(os.Args) < 2 {
		// 没有文件参数，显示书架
		reader.showBookshelf()
		if err := reader.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(1)
		}
		os.Exit(0)
	}

	// 检查帮助参数
	if os.Args[1] == "-h" || os.Args[1] == "--help" {
		fmt.Println("Terminal Novel Reader")
		fmt.Println("Usage: novel-reader <novel-file-path> [page-number]")
		fmt.Println()
		fmt.Println("Navigation:")
		fmt.Println("  Space, f, n, Right Arrow, Ctrl+N  - Next page")
		fmt.Println("  b, p, Left Arrow, Ctrl+P          - Previous page")
		fmt.Println("  Home                              - First page")
		fmt.Println("  End                               - Last page")
		fmt.Println("  g                                 - Go to page")
		fmt.Println()
		fmt.Println("Bookmarks:")
		fmt.Println("  m - Add bookmark")
		fmt.Println("  l - List bookmarks")
		fmt.Println()
		fmt.Println("Bookshelf:")
		fmt.Println("  B - Show bookshelf")
		fmt.Println()
		fmt.Println("Settings:")
		fmt.Println("  s - Settings")
		fmt.Println("  + - Increase font size")
		fmt.Println("  - - Decrease font size")
		fmt.Println()
		fmt.Println("Other:")
		fmt.Println("  h, ? - Show help")
		fmt.Println("  i    - Show reader information")
		fmt.Println("  q    - Quit")
		os.Exit(0)
	}

	// 检查版本参数
	if os.Args[1] == "-v" || os.Args[1] == "--version" {
		fmt.Println("Terminal Novel Reader v1.0.0")
		os.Exit(0)
	}

	filePath := os.Args[1]

	// 加载小说
	if err := reader.LoadNovel(filePath); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	// 检查是否指定了页码
	if len(os.Args) > 2 {
		pageNum, err := strconv.Atoi(os.Args[2])
		if err == nil && pageNum > 0 && pageNum <= reader.totalPages {
			reader.currentPage = pageNum - 1
		}

		// 非交互模式
		reader.DisplayPage(reader.currentPage)
	} else {
		// 交互模式
		if err := reader.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(1)
		}
	}
}
