package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
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
	FontColor       string `json:"font_color"`
	BackgroundColor string `json:"background_color"`
	BorderColor     string `json:"border_color"`
	BorderStyle     string `json:"border_style"` // 边框样式
	FontSize        int    `json:"font_size"`
	MarginTop       int    `json:"margin_top"`
	MarginBottom    int    `json:"margin_bottom"`
	MarginLeft      int    `json:"margin_left"`
	MarginRight     int    `json:"margin_right"`
	PaddingTop      int    `json:"padding_top"`
	PaddingBottom   int    `json:"padding_bottom"`
	PaddingLeft      int    `json:"padding_left"`
	PaddingRight     int    `json:"padding_right"`
	Width           int    `json:"width"`
	Height          int    `json:"height"`
	HeightPercent   int    `json:"height_percent"` // 屏幕高度百分比
	TransparentBg   bool   `json:"transparent_bg"` // 透明背景
	UsePercent      bool   `json:"use_percent"`    // 使用百分比模式
}

// 书签结构体
type Bookmark struct {
	FilePath string `json:"file_path"` // 文件路径
	Page     int    `json:"page"`
	Position int    `json:"position"`
	Note     string `json:"note"`
}

// 阅读器结构体
type NovelReader struct {
	app         *tview.Application
	pages       *tview.Pages
	contentView *tview.TextView
	statusBar   *tview.TextView
	titleBar    *tview.TextView
	flex        *tview.Flex // 主布局
	config      Config
	bookmarks   []Bookmark
	content     []string
	currentPage int
	totalPages  int
	fileName    string
	filePath    string
	width       int
	height      int
	configFile  string
	screen      tcell.Screen
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
	
	nr := &NovelReader{
		app:         tview.NewApplication(),
		pages:       tview.NewPages(),
		contentView: tview.NewTextView(),
		statusBar:   tview.NewTextView(),
		titleBar:    tview.NewTextView(),
		currentPage: 0,
		totalPages:  0,
		width:       80,
		height:      24,
		configFile:  configFile,
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
		},
	}

	// 加载配置
	nr.loadConfig()
	
	// 加载书签
	nr.loadBookmarks()

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

	// 设置标题栏
	nr.titleBar.
		SetDynamicColors(true).
		SetTextAlign(tview.AlignCenter)

	// 设置状态栏
	nr.statusBar.
		SetDynamicColors(true).
		SetTextAlign(tview.AlignRight)

	// 创建主布局
	nr.flex = tview.NewFlex().
		SetDirection(tview.FlexRow).
		AddItem(nr.titleBar, 1, 0, false).
		AddItem(nr.contentView, 0, 1, true).
		AddItem(nr.statusBar, 1, 0, false)

	// 设置边框和边距
	nr.applyConfig()

	// 添加主页面
	nr.pages.AddPage("main", nr.flex, true, true)

	// 设置输入处理
	nr.setupInputHandlers()
}

// 应用配置
func (nr *NovelReader) applyConfig() {
	// 设置颜色
	nr.contentView.SetTextColor(tcell.GetColor(nr.config.FontColor))
	
	// 设置背景颜色（支持透明背景）
	if nr.config.TransparentBg {
		nr.contentView.SetBackgroundColor(tcell.ColorDefault)
		nr.titleBar.SetBackgroundColor(tcell.ColorDefault)
		nr.statusBar.SetBackgroundColor(tcell.ColorDefault)
	} else {
		nr.contentView.SetBackgroundColor(tcell.GetColor(nr.config.BackgroundColor))
		nr.titleBar.SetBackgroundColor(tcell.GetColor(nr.config.BackgroundColor))
		nr.statusBar.SetBackgroundColor(tcell.GetColor(nr.config.BackgroundColor))
	}

	// 设置边框
	nr.contentView.SetBorder(true)
	nr.contentView.SetBorderColor(tcell.GetColor(nr.config.BorderColor))
	
	// 设置边框样式 - 使用默认样式
	// tview的SetBorderStyle方法只需要一个tcell.Style参数
	// 这里我们使用默认样式
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
			case ' ', 'f', 'n': // 空格、f、n 都可以翻页
				nr.nextPage()
				return nil
			case 'b', 'p': // b、p 可以上一页
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
	// fmt.Fprintf(os.Stderr, "Detected encoding: %s\n", encoding)
	// fmt.Fprintf(os.Stderr, "File size: %d bytes\n", len(content))

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

	// fmt.Fprintf(os.Stderr, "Converted content size: %d characters\n", len(utf8Content))
	
	// 检查转换后的内容是否为空
	if len(utf8Content) == 0 {
		fmt.Fprintf(os.Stderr, "Warning: Converted content is empty, trying raw content\n")
		// 尝试直接使用原始内容
		utf8Content = string(content)
		fmt.Fprintf(os.Stderr, "Raw content size: %d characters\n", len(utf8Content))
	}

	// 打印前100字符用于调试
	previewLength := 100
	if len(utf8Content) < previewLength {
		previewLength = len(utf8Content)
	}
	// fmt.Fprintf(os.Stderr, "Content preview: %s\n", string(utf8Content[:previewLength]))

	// 保存文件名和路径
	nr.fileName = filepath.Base(absPath)
	nr.filePath = absPath

	// 处理内容 - 分割为页面
	nr.processContent(utf8Content)

	// 尝试加载阅读进度
	nr.loadProgress()

	// 更新UI
	nr.updateUI()

	return nil
}

// 处理内容并分页
func (nr *NovelReader) processContent(content string) {
	// 直接按行分割，不进行自动换行处理
	lines := strings.Split(content, "\n")
	
	// 计算每页可以显示多少行
	rowsPerPage := nr.height - nr.config.MarginTop - nr.config.MarginBottom -
		nr.config.PaddingTop - nr.config.PaddingBottom - 4 // 4 是标题和状态栏的高度

	if rowsPerPage <= 0 {
		rowsPerPage = 10 // 默认值
	}

	// fmt.Fprintf(os.Stderr, "Rows per page: %d, Total lines: %d\n", rowsPerPage, len(lines))

	// 分割为页面
	nr.content = []string{}
	for i := 0; i < len(lines); i += rowsPerPage {
		end := i + rowsPerPage
		if end > len(lines) {
			end = len(lines)
		}
		pageLines := lines[i:end]
		nr.content = append(nr.content, strings.Join(pageLines, "\n"))
	}

	nr.totalPages = len(nr.content)
	if nr.totalPages == 0 {
		nr.totalPages = 1
		nr.content = []string{"No content - 文件可能为空或编码检测有误"}
	}
	
	// fmt.Fprintf(os.Stderr, "Total pages: %d\n", nr.totalPages)
}

// 更新UI显示
func (nr *NovelReader) updateUI() {
	// 设置标题
	title := fmt.Sprintf("[yellow]%s[-] - Page %d/%d", nr.fileName, nr.currentPage+1, nr.totalPages)
	nr.titleBar.SetText(title)

	// 显示当前页内容
	if nr.currentPage < len(nr.content) {
		nr.contentView.SetText(nr.content[nr.currentPage])
	} else if len(nr.content) > 0 {
		// 如果当前页码超出范围，显示第一页
		nr.currentPage = 0
		nr.contentView.SetText(nr.content[0])
	}

	// 更新状态栏
	progress := fmt.Sprintf("Progress: %d/%d (%.1f%%)",
		nr.currentPage+1, nr.totalPages,
		float64(nr.currentPage+1)/float64(nr.totalPages)*100)
	
	// 更详细的帮助信息
	helpText := fmt.Sprintf("[grey]%s | Q:Quit | ←→/Space:Page | M:Bookmark | L:List | S:Settings | G:Goto | +/-:Size | H:Help[-]", progress)
	nr.statusBar.SetText(helpText)
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
[::b]Terminal Novel Reader Help[::-]

[::b]Navigation:[-]
  Space, f, n, Right Arrow, Ctrl+N  - Next page
  b, p, Left Arrow, Ctrl+P          - Previous page
  Home                              - First page
  End                               - Last page
  g                                 - Go to page

[::b]Bookmarks:[-]
  m - Add bookmark
  l - List bookmarks

[::b]Settings:[-]
  s - Settings
  + - Increase font size (decrease lines per page)
  - - Decrease font size (increase lines per page)

[::b]Other:[-]
  h, ? - Show this help
  i    - Show reader information
  q    - Quit

Press any key to return.
`

	modal := tview.NewModal().
		SetText(helpText).
		AddButtons([]string{"OK"}).
		SetDoneFunc(func(buttonIndex int, buttonLabel string) {
			nr.pages.SwitchToPage("main")
		})

	modal.SetBorder(true).SetTitle("Help")
	nr.pages.AddPage("help", modal, true, true)
}

// 显示阅读器信息
func (nr *NovelReader) showInfo() {
	infoText := fmt.Sprintf(`
[::b]Novel Reader Information[::-]

[::b]File:[-] %s
[::b]Current Page:[-] %d/%d
[::b]Config File:[-] %s
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
		// 没有文件参数，显示书签选择界面
		reader.showBookmarkSelection()
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