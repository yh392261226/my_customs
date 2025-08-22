以下是reader命令的代码:
./book_epub.go
\n=======================\n
package main

import (
	"encoding/xml"
	"errors"
	"os"
	"path/filepath"
	"strings"

	"github.com/mholt/archiver/v3"
	"golang.org/x/net/html"
)

// EpubBook EPUB格式书籍
type EpubBook struct {
	filePath string
	metadata *BookMetadata
	content  []string
	chapters []string
	tempDir  string
}

// EpubPackage EPUB包结构
type EpubPackage struct {
	XMLName  xml.Name `xml:"package"`
	Metadata struct {
		Title       string `xml:"title"`
		Creator     string `xml:"creator"`
		Description string `xml:"description"`
		Publisher   string `xml:"publisher"`
		Date        string `xml:"date"`
		Language    string `xml:"language"`
		Identifier  string `xml:"identifier"`
	} `xml:"metadata"`
	Manifest struct {
		Items []struct {
			ID        string `xml:"id,attr"`
			Href      string `xml:"href,attr"`
			MediaType string `xml:"media-type,attr"`
		} `xml:"item"`
	} `xml:"manifest"`
	Spine struct {
		ItemRefs []struct {
			IDRef string `xml:"idref,attr"`
		} `xml:"itemref"`
	} `xml:"spine"`
}

// NewEpubBook 创建EPUB书籍实例
func NewEpubBook(filePath string) (Book, error) {
	book := &EpubBook{
		filePath: filePath,
		metadata: &BookMetadata{
			Title: filepath.Base(filePath),
		},
	}

	// 创建临时目录
	tempDir, err := os.MkdirTemp("", "novel-reader-epub")
	if err != nil {
		return nil, err
	}
	book.tempDir = tempDir

	// 解压EPUB文件
	err = archiver.Unarchive(filePath, tempDir)
	if err != nil {
		book.Close()
		return nil, err
	}

	// 解析元数据
	err = book.parseMetadata()
	if err != nil {
		book.Close()
		return nil, err
	}

	// 解析内容
	err = book.parseContent()
	if err != nil {
		book.Close()
		return nil, err
	}

	return book, nil
}

// parseMetadata 解析元数据
func (b *EpubBook) parseMetadata() error {
	// 查找OPF文件
	containerPath := filepath.Join(b.tempDir, "META-INF", "container.xml")
	containerFile, err := os.Open(containerPath)
	if err != nil {
		return err
	}
	defer containerFile.Close()

	var container struct {
		RootFiles []struct {
			FullPath string `xml:"full-path,attr"`
		} `xml:"rootfiles>rootfile"`
	}

	decoder := xml.NewDecoder(containerFile)
	if err := decoder.Decode(&container); err != nil {
		return err
	}

	if len(container.RootFiles) == 0 {
		return errors.New("未找到OPF文件")
	}

	// 解析OPF文件
	opfPath := filepath.Join(b.tempDir, container.RootFiles[0].FullPath)
	opfFile, err := os.Open(opfPath)
	if err != nil {
		return err
	}
	defer opfFile.Close()

	var pkg EpubPackage
	decoder = xml.NewDecoder(opfFile)
	if err := decoder.Decode(&pkg); err != nil {
		return err
	}

	// 设置元数据
	b.metadata.Title = pkg.Metadata.Title
	b.metadata.Author = pkg.Metadata.Creator
	b.metadata.Description = pkg.Metadata.Description
	b.metadata.Publisher = pkg.Metadata.Publisher
	b.metadata.Published = pkg.Metadata.Date
	b.metadata.Language = pkg.Metadata.Language
	b.metadata.ISBN = pkg.Metadata.Identifier

	// 查找封面
	for _, item := range pkg.Manifest.Items {
		if strings.Contains(item.MediaType, "image") && 
		   (strings.Contains(strings.ToLower(item.Href), "cover") || 
		    strings.Contains(strings.ToLower(item.ID), "cover")) {
			coverPath := filepath.Join(filepath.Dir(opfPath), item.Href)
			coverData, err := os.ReadFile(coverPath)
			if err == nil {
				b.metadata.Cover = coverData
				break
			}
		}
	}

	return nil
}

// parseContent 解析内容
func (b *EpubBook) parseContent() error {
	// 查找OPF文件
	containerPath := filepath.Join(b.tempDir, "META-INF", "container.xml")
	containerFile, err := os.Open(containerPath)
	if err != nil {
		return err
	}
	defer containerFile.Close()

	var container struct {
		RootFiles []struct {
			FullPath string `xml:"full-path,attr"`
		} `xml:"rootfiles>rootfile"`
	}

	decoder := xml.NewDecoder(containerFile)
	if err := decoder.Decode(&container); err != nil {
		return err
	}

	if len(container.RootFiles) == 0 {
		return errors.New("未找到OPF文件")
	}

	// 解析OPF文件
	opfPath := filepath.Join(b.tempDir, container.RootFiles[0].FullPath)
	opfFile, err := os.Open(opfPath)
	if err != nil {
		return err
	}
	defer opfFile.Close()

	var pkg EpubPackage
	decoder = xml.NewDecoder(opfFile)
	if err := decoder.Decode(&pkg); err != nil {
		return err
	}

	// 创建ID到文件路径的映射
	itemMap := make(map[string]string)
	for _, item := range pkg.Manifest.Items {
		if strings.Contains(item.MediaType, "html") || 
		   strings.Contains(item.MediaType, "xhtml") {
			itemMap[item.ID] = filepath.Join(filepath.Dir(opfPath), item.Href)
		}
	}

	// 按阅读顺序获取内容
	var allContent []string
	for _, itemRef := range pkg.Spine.ItemRefs {
		if filePath, exists := itemMap[itemRef.IDRef]; exists {
			content, err := b.parseHtmlFile(filePath)
			if err != nil {
				return err
			}
			allContent = append(allContent, content...)
			b.chapters = append(b.chapters, filePath)
		}
	}

	// 处理内容
	b.content = processContent(allContent, &Config{
		Width:  80,
		Height: 24,
	})

	return nil
}

// parseHtmlFile 解析HTML文件
func (b *EpubBook) parseHtmlFile(filePath string) ([]string, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	// 解析HTML
	doc, err := html.Parse(file)
	if err != nil {
		return nil, err
	}

	// 提取文本内容
	var content []string
	var extractText func(*html.Node)
	extractText = func(n *html.Node) {
		if n.Type == html.TextNode {
			text := strings.TrimSpace(n.Data)
			if text != "" {
				content = append(content, text)
			}
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			extractText(c)
		}
	}
	extractText(doc)

	return content, nil
}

// GetMetadata 获取元数据
func (b *EpubBook) GetMetadata() *BookMetadata {
	return b.metadata
}

// GetContent 获取内容
func (b *EpubBook) GetContent() ([]string, error) {
	return b.content, nil
}

// GetChapter 获取章节
func (b *EpubBook) GetChapter(index int) ([]string, error) {
	if index < 0 || index >= len(b.chapters) {
		return nil, errors.New("章节索引超出范围")
	}

	content, err := b.parseHtmlFile(b.chapters[index])
	if err != nil {
		return nil, err
	}

	return processContent(content, &Config{
		Width:  80,
		Height: 24,
	}), nil
}

// GetCover 获取封面
func (b *EpubBook) GetCover() ([]byte, error) {
	return b.metadata.Cover, nil
}

// Close 关闭书籍
func (b *EpubBook) Close() error {
	if b.tempDir != "" {
		return os.RemoveAll(b.tempDir)
	}
	return nil
}

./book_txt.go
\n=======================\n
package main

import (
	"path/filepath"
)

// TxtBook TXT格式书籍
type TxtBook struct {
	filePath string
	metadata *BookMetadata
	content  []string
}

// NewTxtBook 创建TXT书籍实例
func NewTxtBook(filePath string) (Book, error) {
	book := &TxtBook{
		filePath: filePath,
		metadata: &BookMetadata{
			Title: filepath.Base(filePath),
		},
	}

	// 读取内容
	content, err := readFileWithEncodingDetection(filePath)
	if err != nil {
		return nil, err
	}
	
	book.content = processContent(content, &Config{
		Width:  80,
		Height: 24,
	})
	
	return book, nil
}

// GetMetadata 获取元数据
func (b *TxtBook) GetMetadata() *BookMetadata {
	return b.metadata
}

// GetContent 获取内容
func (b *TxtBook) GetContent() ([]string, error) {
	return b.content, nil
}

// GetChapter 获取章节
func (b *TxtBook) GetChapter(index int) ([]string, error) {
	// TXT格式没有明确的章节划分，返回全部内容
	return b.content, nil
}

// GetCover 获取封面
func (b *TxtBook) GetCover() ([]byte, error) {
	// TXT格式没有封面
	return nil, nil
}

// Close 关闭书籍
func (b *TxtBook) Close() error {
	// TXT格式不需要特殊清理
	return nil
}

./book.go
\n=======================\n
package main

import (
	"bufio"
	"errors"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"unicode/utf8"

	"github.com/mattn/go-runewidth"
	"golang.org/x/text/encoding"
	"golang.org/x/text/encoding/charmap"
	"golang.org/x/text/encoding/simplifiedchinese"
	"golang.org/x/text/encoding/traditionalchinese"
	"golang.org/x/text/encoding/unicode"
	"golang.org/x/text/transform"
)

// readFileWithEncodingDetection 读取文件并自动检测编码，支持大文件
func readFileWithEncodingDetection(filePath string) ([]string, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	// 获取文件大小
	fileInfo, err := file.Stat()
	if err != nil {
		return nil, err
	}
	fileSize := fileInfo.Size()

	// 读取文件前4KB用于编码检测
	bufferSize := 4096
	if fileSize < int64(bufferSize) {
		bufferSize = int(fileSize)
	}
	
	buffer := make([]byte, bufferSize)
	n, err := file.Read(buffer)
	if err != nil && err != io.EOF {
		return nil, err
	}

	// 检测编码
	detectedEncoding := detectEncoding(buffer[:n])

	// 重置文件指针
	file.Seek(0, 0)

	var decoder *encoding.Decoder
	switch detectedEncoding {
	case "gbk":
		decoder = simplifiedchinese.GBK.NewDecoder()
	case "gb18030":
		decoder = simplifiedchinese.GB18030.NewDecoder()
	case "big5":
		decoder = traditionalchinese.Big5.NewDecoder()
	case "windows-1252":
		decoder = charmap.Windows1252.NewDecoder()
	case "utf-16be":
		decoder = unicode.UTF16(unicode.BigEndian, unicode.UseBOM).NewDecoder()
	case "utf-16le":
		decoder = unicode.UTF16(unicode.LittleEndian, unicode.UseBOM).NewDecoder()
	default:
		// 默认UTF-8
		decoder = encoding.Nop.NewDecoder()
	}

	// 使用检测到的编码读取文件
	reader := transform.NewReader(file, decoder)
	
	// 使用 bufio.Reader 而不是 Scanner 来避免 "token too long" 错误
	bufReader := bufio.NewReader(reader)
	var lines []string
	
	for {
		line, err := bufReader.ReadString('\n')
		if err != nil && err != io.EOF {
			return nil, err
		}
		
		// 去除行尾的换行符
		if len(line) > 0 && line[len(line)-1] == '\n' {
			line = line[:len(line)-1]
		}
		if len(line) > 0 && line[len(line)-1] == '\r' {
			line = line[:len(line)-1]
		}
		
		lines = append(lines, line)
		
		if err == io.EOF {
			break
		}
	}

	return lines, nil
}

// detectEncoding 检测文本编码
func detectEncoding(data []byte) string {
	// UTF-8 BOM检测
	if len(data) >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF {
		return "utf-8"
	}

	// UTF-16 BE BOM检测
	if len(data) >= 2 && data[0] == 0xFE && data[1] == 0xFF {
		return "utf-16be"
	}

	// UTF-16 LE BOM检测
	if len(data) >= 2 && data[0] == 0xFF && data[1] == 0xFE {
		return "utf-16le"
	}

	// 尝试检测中文编码
	if isGBK(data) {
		return "gbk"
	}

	if isBig5(data) {
		return "big5"
	}

	// 检查是否为有效的UTF-8
	if utf8.Valid(data) {
		return "utf-8"
	}

	// 默认返回UTF-8
	return "utf-8"
}

// isGBK 检测是否是GBK编码
func isGBK(data []byte) bool {
	length := len(data)
	var i int = 0
	for i < length {
		if data[i] <= 0x7f {
			// 编码小于等于127的为ASCII字符
			i++
			continue
		} else {
			// 大于127的为非ASCII字符，可能是GBK编码
			if i+1 < length {
				// 双字节字符
				if data[i] >= 0x81 && data[i] <= 0xfe &&
					data[i+1] >= 0x40 && data[i+1] <= 0xfe && data[i+1] != 0x7f {
					i += 2
					continue
				} else {
					return false
				}
			} else {
				return false
			}
		}
	}
	return true
}

// isBig5 检测是否是Big5编码
func isBig5(data []byte) bool {
	length := len(data)
	var i int = 0
	for i < length {
		if data[i] <= 0x7f {
			// 编码小于等于127的为ASCII字符
			i++
			continue
		} else {
			// 大于127的为非ASCII字符，可能是Big5编码
			if i+1 < length {
				// 双字节字符
				if data[i] >= 0xa1 && data[i] <= 0xfe &&
					(data[i+1] >= 0x40 && data[i+1] <= 0x7e || data[i+1] >= 0xa1 && data[i+1] <= 0xfe) {
					i += 2
					continue
				} else {
					return false
				}
			} else {
				return false
			}
		}
	}
	return true
}

// processContent 处理内容，包括自动换行和分章
func processContent(lines []string, config *Config) []string {
	var processedPages []string
	var currentPage strings.Builder
	currentLineLength := 0
	maxWidth := config.Width - 2*config.Margin - 2*config.Padding
	maxHeight := config.Height - 2*config.Margin - 2*config.Padding - 2 // 标题和进度条占用的行

	// 章节检测正则表达式 - 增强匹配模式
	chapterRegexes := []*regexp.Regexp{
		regexp.MustCompile(`^(第[零一二三四五六七八九十百千]+章\s*[^\s]{0,20})`),
		regexp.MustCompile(`^(第[0-9]+章\s*[^\s]{0,20})`),
		regexp.MustCompile(`^(卷[零一二三四五六七八九十百千]+\s*[^\s]{0,20})`),
		regexp.MustCompile(`^([0-9]+\.[0-9]+\s+[^\s]{0,20})`),
		regexp.MustCompile(`^([一二三四五六七八九十]+、\s*[^\s]{0,20})`),
	}

	for _, line := range lines {
		// 去除首尾空白字符
		line = strings.TrimSpace(line)
		
		// 跳过空行
		if line == "" {
			continue
		}

		// 检测章节标题
		isChapter := false
		for _, regex := range chapterRegexes {
			if regex.MatchString(line) {
				isChapter = true
				break
			}
		}

		if isChapter {
			// 如果当前页有内容，先保存当前页
			if currentPage.Len() > 0 {
				processedPages = append(processedPages, currentPage.String())
				currentPage.Reset()
				currentLineLength = 0
			}
			
			// 将章节标题单独作为一页
			processedPages = append(processedPages, line)
			continue
		}

		// 处理普通文本，自动换行
		words := strings.Fields(line)
		for _, word := range words {
			wordWidth := runewidth.StringWidth(word)
			
			// 如果当前行加上这个词会超出宽度，则换行
			if currentLineLength+wordWidth+1 > maxWidth {
				currentPage.WriteString("\n")
				currentLineLength = 0
			}
			
			// 如果不是行首，添加空格
			if currentLineLength > 0 {
				currentPage.WriteString(" ")
				currentLineLength++
			}
			
			currentPage.WriteString(word)
			currentLineLength += wordWidth
			
			// 如果当前页行数达到最大高度，保存当前页并开始新页
			if strings.Count(currentPage.String(), "\n") >= maxHeight {
				processedPages = append(processedPages, currentPage.String())
				currentPage.Reset()
				currentLineLength = 0
			}
		}
		
		// 一行处理完后换行
		currentPage.WriteString("\n")
		currentLineLength = 0
	}

	// 添加最后一页
	if currentPage.Len() > 0 {
		processedPages = append(processedPages, currentPage.String())
	}

	return processedPages
}

// BookMetadata 书籍元数据
type BookMetadata struct {
	Title       string   `json:"title"`
	Author      string   `json:"author"`
	Description string   `json:"description"`
	Publisher   string   `json:"publisher"`
	Published   string   `json:"published"`
	Language    string   `json:"language"`
	ISBN        string   `json:"isbn"`
	Cover       []byte   `json:"cover"`
	Chapters    []string `json:"chapters"`
}

// Book 书籍接口
type Book interface {
	// 元数据
	GetMetadata() *BookMetadata
	// 内容
	GetContent() ([]string, error)
	// 获取特定章节
	GetChapter(index int) ([]string, error)
	// 获取封面
	GetCover() ([]byte, error)
	// 关闭书籍
	Close() error
}

// BookType 书籍类型
type BookType int

const (
	BookTypeTXT BookType = iota
	BookTypeEPUB
	BookTypePDF
	BookTypeMOBI
	BookTypeUnknown
)

// 根据文件扩展名检测书籍类型
func detectBookType(filePath string) BookType {
    ext := strings.ToLower(filepath.Ext(filePath))
    switch ext {
    case ".txt":
        return BookTypeTXT
    case ".epub":
        return BookTypeEPUB
    case ".mobi", ".pdf", ".azw", ".azw3":
        // 暂时不支持MOBI格式
        return BookTypeUnknown
    default:
        return BookTypeUnknown
    }
}

// OpenBook 打开书籍文件
func OpenBook(filePath string) (Book, error) {
	// 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return nil, errors.New("文件不存在")
	}

	bookType := detectBookType(filePath)
	
	switch bookType {
	case BookTypeTXT:
		return NewTxtBook(filePath)
	case BookTypeEPUB:
		return NewEpubBook(filePath)
	// case BookTypePDF:
	// 	return nil, errors.New("PDF格式支持暂时不可用")
	// case BookTypeMOBI:
	// 	return NewMobiBook(filePath)
	default:
		return nil, errors.New("不支持的格式")
	}
}

./config.go
\n=======================\n
package main

import (
	"encoding/json"
	"os"
	"path/filepath"
)

// loadConfig 加载配置
func loadConfig() *Config {
	configPath := getConfigPath()
	
	// 如果配置文件不存在，使用默认配置
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return &defaultConfig
	}
	
	// 读取配置文件
	file, err := os.Open(configPath)
	if err != nil {
		return &defaultConfig
	}
	defer file.Close()
	
	var config Config
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&config); err != nil {
		return &defaultConfig
	}
	
	return &config
}

// saveConfig 保存配置
func saveConfig(config *Config) error {
	configPath := getConfigPath()
	
	// 确保配置目录存在
	configDir := filepath.Dir(configPath)
	if err := os.MkdirAll(configDir, 0755); err != nil {
		return err
	}
	
	file, err := os.Create(configPath)
	if err != nil {
		return err
	}
	defer file.Close()
	
	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(config)
}

// getConfigPath 获取配置文件路径
func getConfigPath() string {
	homeDir, _ := os.UserHomeDir()
	return filepath.Join(homeDir, ".config", "novel-reader", "config.json")
}

./main.go
\n=======================\n
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"golang.org/x/term"
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
	
	// 检查是否是终端设备
	isTerminal := term.IsTerminal(int(os.Stdin.Fd()))
	if !isTerminal {
		// 如果不是终端设备，直接输出内容并退出
		// 使用 reader.Content 而不是 reader.GetContent()
		for _, page := range reader.Content {
			fmt.Println(page)
			fmt.Println("---")
		}
		return
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

./reader.go
\n=======================\n
package main

import (
	"bufio"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"time"

	"golang.org/x/term"
)

// TTSPlayer 文本转语音播放器
type TTSPlayer struct {
    cmd     *exec.Cmd
    mutex   sync.Mutex
    playing bool
    stopCh  chan struct{}
}

// Note 笔记结构
type Note struct {
	File    string `json:"file"`
	Page    int    `json:"page"`
	Content string `json:"content"`
}

// ReadingStats 阅读统计
type ReadingStats struct {
    TotalReadingTime int64 `json:"totalReadingTime"` // 总阅读时间（秒）
    PagesRead        int   `json:"pagesRead"`        // 已读页数
    BooksCompleted   int   `json:"booksCompleted"`   // 完成的书籍数量
    LastReadTime     int64 `json:"lastReadTime"`     // 最后阅读时间
    LastPage         int   `json:"lastPage"`         // 最后阅读的页码
}

// Reader 阅读器结构体
type Reader struct {
	FilePath       string
	Content        []string
	CurrentPage    int
	TotalPages     int
	Config         *Config
	Bookmarks      []Bookmark
	CurrentTTS     *TTSPlayer
	SearchTerm     string
	SearchResults  []int
	CurrentSearch  int
	IsInSetting    bool
	IsInBookmark   bool
	IsInSearch     bool
	Notes          []Note
	ReadingStats   *ReadingStats
	Book           Book          // 书籍实例
	BookTitle      string        // 书籍标题
    AutoFlipTicker   *time.Ticker  // 自动翻页计时器
	AutoFlipQuit     chan struct{} // 自动翻页退出通道
    RemindTicker     *time.Ticker  // 提醒计时器
	RemindQuit       chan struct{} // 提醒退出通道
	StartReadingTime time.Time     // 开始阅读时间
}

// NewTTSPlayer 创建新的TTS播放器
func NewTTSPlayer() *TTSPlayer {
	return &TTSPlayer{
		playing: false,
	}
}

// PlayText 播放文本
func (t *TTSPlayer) PlayText(text string, speed int) error {
    t.mutex.Lock()
    defer t.mutex.Unlock()

    // 如果正在播放，先停止
    if t.playing {
        t.stopCh <- struct{}{}
        if t.cmd != nil && t.cmd.Process != nil {
            t.cmd.Process.Kill()
        }
        t.playing = false
    }

    // 根据操作系统选择不同的TTS命令
    var cmd *exec.Cmd
    if isLinux() {
        // Linux使用espeak
        cmd = exec.Command("espeak", "-s", strconv.Itoa(speed*30), text)
    } else if isMacOS() {
        // macOS使用say
        rate := mapSpeedToRate(speed)
        cmd = exec.Command("say", "-r", rate, text)
    } else if isWindows() {
        // Windows使用PowerShell的SpeechSynthesizer
        psScript := fmt.Sprintf(
            `Add-Type -AssemblyName System.speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Rate = %d; $speak.Speak("%s");`,
            (speed-5)*2, // 将速度映射到-10到10范围
            strings.ReplaceAll(text, `"`, `\"`),
        )
        cmd = exec.Command("powershell", "-Command", psScript)
    } else {
        return fmt.Errorf("不支持的操作系统")
    }

    t.cmd = cmd
    t.playing = true
    t.stopCh = make(chan struct{}, 1)

    // 启动TTS进程
    go func() {
        err := cmd.Run()
        
        t.mutex.Lock()
        defer t.mutex.Unlock()
        
        // 检查是否是被主动停止的
        select {
        case <-t.stopCh:
            // 是被主动停止的，不更新状态
        default:
            t.playing = false
        }
        
        if err != nil && err.Error() != "signal: killed" {
            fmt.Printf("TTS错误: %v\n", err)
        }
    }()

    return nil
}

// Stop 停止播放
func (t *TTSPlayer) Stop() {
    t.mutex.Lock()
    defer t.mutex.Unlock()

    if t.playing {
        t.stopCh <- struct{}{}
        if t.cmd != nil && t.cmd.Process != nil {
            t.cmd.Process.Kill()
        }
        t.playing = false
    }
}

// IsPlaying 检查是否正在播放
func (t *TTSPlayer) IsPlaying() bool {
    t.mutex.Lock()
    defer t.mutex.Unlock()
    return t.playing
}

// 辅助函数：检测操作系统
func isLinux() bool {
	return strings.Contains(strings.ToLower(os.Getenv("OS")), "linux") ||
		strings.Contains(strings.ToLower(runtime.GOOS), "linux")
}

func isMacOS() bool {
	return strings.Contains(strings.ToLower(os.Getenv("OS")), "darwin") ||
		strings.Contains(strings.ToLower(runtime.GOOS), "darwin")
}

func isWindows() bool {
	return strings.Contains(strings.ToLower(os.Getenv("OS")), "windows") ||
		strings.Contains(strings.ToLower(runtime.GOOS), "windows")
}

// 将速度值映射到macOS的语速范围
func mapSpeedToRate(speed int) string {
	// 将1-10的速度映射到150-300的语速范围
	rate := 150 + (speed-1)*15
	return strconv.Itoa(rate)
}

// NewReader 创建新的阅读器实例
func NewReader(filePath string) (*Reader, error) {
	// 加载配置
	config := loadConfig()

	// 打开书籍文件
	book, err := OpenBook(filePath)
	if err != nil {
		return nil, err
	}

	// 获取书籍内容
	content, err := book.GetContent()
	if err != nil {
		book.Close()
		return nil, err
	}

	// 获取书籍元数据
	metadata := book.GetMetadata()

	reader := &Reader{
		FilePath:    filePath,
		Content:     content,
		CurrentPage: 0,
		TotalPages:  len(content),
		Config:      config,
		Book:        book, // 保存书籍实例
		BookTitle:   metadata.Title, // 保存书籍标题
        StartReadingTime: time.Now(), // 记录开始阅读时间
	}
    // 启动提醒计时器
    if config.RemindInterval > 0 {
        reader.startRemindTimer()
    }

	// 加载书签
	reader.Bookmarks = loadBookmarksForFile(filePath)

	// 加载笔记
	reader.Notes = loadNotes(filePath)

	// 加载阅读统计
	reader.ReadingStats = loadReadingStats(filePath)
	
	// 如果存在阅读统计，恢复上次阅读位置
	if reader.ReadingStats != nil && reader.ReadingStats.LastPage > 0 {
		// 确保页码在有效范围内
		if reader.ReadingStats.LastPage < reader.TotalPages {
			reader.CurrentPage = reader.ReadingStats.LastPage
		} else {
			reader.CurrentPage = reader.TotalPages - 1
		}
	}

	return reader, nil
}

// Run 启动阅读器主循环
func (r *Reader) Run() error {
	// 初始化TTS
	r.CurrentTTS = NewTTSPlayer()

	// 初始化阅读统计
	if r.ReadingStats == nil {
		r.ReadingStats = &ReadingStats{}
	}

	// 记录开始阅读时间
	startTime := time.Now().Unix()

	// 检查标准输入是否是终端设备
	isTerminal := term.IsTerminal(int(os.Stdin.Fd()))
	
	// 只有在终端设备上才初始化UI
	if isTerminal {
		if err := initUI(); err != nil {
			return err
		}
		defer cleanupUI()
	}

    // 确保书籍被关闭
	defer r.Book.Close()

    // 确保自动翻页被停止
    defer r.stopAutoFlip()

    // 如果配置启用了自动翻页，启动它
    if r.Config.AutoFlipEnabled && r.Config.AutoFlipInterval > 0 {
        r.startAutoFlip()
    }

	// 只有在终端设备上才渲染页面
	if isTerminal {
		r.RenderPage()
	}

	// 主事件循环
	for {
		// 处理输入
		key, err := getInput()
		if err != nil {
			return err
		}

		// 如果在隐藏状态，只响应i键
		if isWindowHidden {
			if key == "i" {
				r.HideWindow()
				// 恢复后重新渲染页面
				r.RenderPage()
			}
			// 忽略其他所有按键
			continue
		}

		// 处理按键
		switch key {
		case "up", "left", " ":
			r.PreviousPage()
		case "down", "right":
			r.NextPage()
		case "s":
			if isTerminal {
				r.ShowSettings()
			}
		case "h":
			if isTerminal {
				r.ShowHelp()
			}
		case "f":
			if isTerminal {
				r.ShowBookmarks()
			}
		case "b":
			if isTerminal {
				r.ToggleBookmark()
			}
		case "/":
			if isTerminal {
				r.StartSearch()
			}
		case "r":
			r.ToggleReadAloud()
		case "q":
			// 更新阅读统计
			r.updateReadingStats(startTime)
			return nil
		case "i":  // 隐藏/显示窗口
			if isTerminal {
				r.HideWindow()
			}
		case "g":
			if isTerminal {
				r.GoToBookmark()
			}
		case "l":
			if isTerminal {
				r.GoToPage()
			}
		case "n":
			r.NextSearchResult()
		case "p":
			r.PreviousSearchResult()
		case "t": // 添加笔记
			if isTerminal {
				r.AddNote()
			}
		case "v": // 查看笔记
			if isTerminal {
				r.ShowNotes()
			}
		case "e": // 导出数据
			if isTerminal {
				r.ExportData()
			}
		case "x": // 查看阅读统计
			if isTerminal {
				r.ShowReadingStats()
			}
        case "a": // 自动翻页
            if r.Config.AutoFlipEnabled {
                r.stopAutoFlip()
            } else {
                r.startAutoFlip()
            }
            // 立即重新渲染以显示状态变化
            if isTerminal {
				r.RenderPage()
			}
		case "esc":
			if r.IsInSetting || r.IsInBookmark || r.IsInSearch {
                r.IsInSetting = false
                r.IsInBookmark = false
                r.IsInSearch = false
            } else {
                // 更新阅读统计
                r.updateReadingStats(startTime)
                // 停止自动翻页
                r.stopAutoFlip()
                return nil
            }
		}

		// 只有在终端设备上才重新渲染页面
		if isTerminal {
			r.RenderPage()
		}
	}
}

// RenderPage 渲染当前页
func (r *Reader) RenderPage() {
    if isWindowHidden {
        return
    }

    clearScreen()

    // 绘制边框
    if r.Config.BorderStyle != "none" {
        drawBorder(r.Config.BorderStyle, r.Config.Width, r.Config.Height)
    }

    // 计算内容区域
    contentWidth := r.Config.Width - 2*r.Config.Margin - 2*r.Config.Padding
    contentHeight := r.Config.Height - 2*r.Config.Margin - 2*r.Config.Padding - 4 // 增加底部信息行

    // 显示标题
    var title string
    if r.BookTitle == "" {
        title = fmt.Sprintf("《%s》", getFileName(r.FilePath))
    } else {
        title = fmt.Sprintf("《%s》", r.BookTitle)
    }
    displayText(1+r.Config.Margin, 0+r.Config.Margin, title, r.Config.FontColor, r.Config.BgColor)

    // 显示内容
    if r.CurrentPage < len(r.Content) {
        lines := wrapText(r.Content[r.CurrentPage], contentWidth)
        for i, line := range lines {
            if i >= contentHeight {
                break
            }
            yPos := 1 + i + r.Config.Margin + r.Config.Padding
            displayText(1+r.Config.Margin+r.Config.Padding, yPos, line, r.Config.FontColor, r.Config.BgColor)
        }
    }

    // 显示进度
	var progressStr string
	if r.Config.ShowProgress {
		// 计算百分比
		percentage := float64(r.CurrentPage+1) / float64(r.TotalPages) * 100
		progressStr = fmt.Sprintf("进度: %d/%d (%.1f%%)",
			r.CurrentPage+1, r.TotalPages, percentage)
		
		// 显示进度条
		displayProgressBar(1+r.Config.Margin, r.Config.Height-4-r.Config.Margin,
			r.Config.Width-2*r.Config.Margin, r.CurrentPage+1, r.TotalPages,
			r.Config.FontColor, r.Config.BgColor)
	}

	// 绘制底部状态栏
	shortcuts := getShortcutHint()
	drawBottomStatusBar(r.Config.BorderStyle, r.Config.Width, r.Config.Height, 
		progressStr, shortcuts, r.Config.FontColor, r.Config.BgColor)

    // 显示搜索高亮
    if r.SearchTerm != "" {
        r.highlightSearchTerms()
    }

    // 显示当前模式提示
    modeLine := ""
    if r.IsInSetting {
        modeLine = "设置模式 - 按ESC退出"
    } else if r.IsInBookmark {
        modeLine = "书签模式 - 按ESC退出"
    } else if r.IsInSearch {
        modeLine = fmt.Sprintf("搜索模式: %s (%d/%d) - 按ESC退出", 
            r.SearchTerm, r.CurrentSearch+1, len(r.SearchResults))
    }
    
    if modeLine != "" {
        displayText(1+r.Config.Margin, r.Config.Height-4-r.Config.Margin, modeLine, r.Config.FontColor, r.Config.BgColor)
    }

    // 显示朗读状态
    if r.CurrentTTS.IsPlaying() {
        statusText := "朗读中..."
        displayText(r.Config.Width-len(statusText)-r.Config.Margin-1, 0, statusText, r.Config.FontColor, r.Config.BgColor)
    }

    // 显示自动翻页状态
    if r.Config.AutoFlipEnabled {
        statusText := fmt.Sprintf("自动翻页中(%ds)", r.Config.AutoFlipInterval)
        // 确保状态文本不会超出屏幕
        if len(statusText) > r.Config.Width-2 {
            statusText = statusText[:r.Config.Width-2]
        }
        displayText(r.Config.Width-len(statusText)-r.Config.Margin-1, 1, statusText, r.Config.FontColor, r.Config.BgColor)
    }
}

// PreviousPage 上一页
func (r *Reader) PreviousPage() {
	if r.CurrentPage > 0 {
		r.CurrentPage--
	}
}

// NextPage 下一页
func (r *Reader) NextPage() {
	if r.CurrentPage < r.TotalPages-1 {
		r.CurrentPage++
	}
}

// ShowSettings 显示设置界面
func (r *Reader) ShowSettings() {
    r.IsInSetting = true
    
    // 设置选项
    options := []string{
        "宽度: " + strconv.Itoa(r.Config.Width),
        "高度: " + strconv.Itoa(r.Config.Height),
        "字体大小: " + strconv.Itoa(r.Config.FontSize),
        "字体颜色: " + r.Config.FontColor,
        "背景颜色: " + r.Config.BgColor,
        "边框样式: " + r.Config.BorderStyle,
        "显示进度条: " + strconv.FormatBool(r.Config.ShowProgress),
        "边距: " + strconv.Itoa(r.Config.Margin),
        "内边距: " + strconv.Itoa(r.Config.Padding),
        "行间距: " + strconv.Itoa(r.Config.LineSpacing),
        "朗读速度: " + strconv.Itoa(r.Config.TTSSpeed),
        "自动朗读: " + strconv.FormatBool(r.Config.AutoReadAloud),
        "自动翻页间隔: " + strconv.Itoa(r.Config.AutoFlipInterval) + "秒",
        "自动翻页: " + strconv.FormatBool(r.Config.AutoFlipEnabled),
        "阅读提醒间隔: " + strconv.Itoa(r.Config.RemindInterval) + "分钟",
        "保存并退出",
    }
    
    selected := 0
    for r.IsInSetting {
        clearScreen()
        
        // 计算居中位置
        _, height, _ := getTerminalSize()
        startY := (height - len(options) - 3) / 2
        
        // 显示标题
        displayText(2, startY, "设置 - 使用上下键选择，回车键修改，ESC退出", r.Config.FontColor, r.Config.BgColor)
        displayText(2, startY+1, "========================================", r.Config.FontColor, r.Config.BgColor)
        
        // 显示选项
        for i, option := range options {
            y := startY + 2 + i
            if i == selected {
                displayText(2, y, "> "+option, r.Config.FontColor, r.Config.BgColor)
            } else {
                displayText(2, y, "  "+option, r.Config.FontColor, r.Config.BgColor)
            }
        }
        
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
            r.modifySetting(selected)
            // 更新选项显示
            options = []string{
                "宽度: " + strconv.Itoa(r.Config.Width),
                "高度: " + strconv.Itoa(r.Config.Height),
                "字体大小: " + strconv.Itoa(r.Config.FontSize),
                "字体颜色: " + r.Config.FontColor,
                "背景颜色: " + r.Config.BgColor,
                "边框样式: " + r.Config.BorderStyle,
                "显示进度条: " + strconv.FormatBool(r.Config.ShowProgress),
                "边距: " + strconv.Itoa(r.Config.Margin),
                "内边距: " + strconv.Itoa(r.Config.Padding),
                "行间距: " + strconv.Itoa(r.Config.LineSpacing),
                "朗读速度: " + strconv.Itoa(r.Config.TTSSpeed),
                "自动朗读: " + strconv.FormatBool(r.Config.AutoReadAloud),
                "自动翻页间隔: " + strconv.Itoa(r.Config.AutoFlipInterval) + "秒",
                "自动翻页: " + strconv.FormatBool(r.Config.AutoFlipEnabled),
                "阅读提醒间隔: " + strconv.Itoa(r.Config.RemindInterval) + "分钟",
                "保存并退出",
            }
        case "esc":
            r.IsInSetting = false
            // 保存配置
            saveConfig(r.Config)
            return
        }
    }
}

// modifySetting 修改设置项
func (r *Reader) modifySetting(selected int) {
	switch selected {
	case 0: // 宽度
		input := showInputPrompt("请输入宽度: ")
		if width, err := strconv.Atoi(input); err == nil && width > 0 {
			r.Config.Width = width
		}
	case 1: // 高度
		input := showInputPrompt("请输入高度: ")
		if height, err := strconv.Atoi(input); err == nil && height > 0 {
			r.Config.Height = height
		}
	case 2: // 字体大小
		input := showInputPrompt("请输入字体大小: ")
		if size, err := strconv.Atoi(input); err == nil && size > 0 {
			r.Config.FontSize = size
		}
	case 3: // 字体颜色
		colors := []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"}
		currentIndex := 0
		for i, color := range colors {
			if color == r.Config.FontColor {
				currentIndex = i
				break
			}
		}
		nextIndex := (currentIndex + 1) % len(colors)
		r.Config.FontColor = colors[nextIndex]
	case 4: // 背景颜色
		colors := []string{"black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "transparent"}
		currentIndex := 0
		for i, color := range colors {
			if color == r.Config.BgColor {
				currentIndex = i
				break
			}
		}
		nextIndex := (currentIndex + 1) % len(colors)
		r.Config.BgColor = colors[nextIndex]
	case 5: // 边框样式
		styles := []string{"round", "bold", "double", "thin", "none"}
		currentIndex := 0
		for i, style := range styles {
			if style == r.Config.BorderStyle {
				currentIndex = i
				break
			}
		}
		nextIndex := (currentIndex + 1) % len(styles)
		r.Config.BorderStyle = styles[nextIndex]
	case 6: // 显示进度条
		r.Config.ShowProgress = !r.Config.ShowProgress
	case 7: // 边距
		input := showInputPrompt("请输入边距: ")
		if margin, err := strconv.Atoi(input); err == nil && margin >= 0 {
			r.Config.Margin = margin
		}
	case 8: // 内边距
		input := showInputPrompt("请输入内边距: ")
		if padding, err := strconv.Atoi(input); err == nil && padding >= 0 {
			r.Config.Padding = padding
		}
	case 9: // 行间距
		input := showInputPrompt("请输入行间距: ")
		if spacing, err := strconv.Atoi(input); err == nil && spacing >= 0 {
			r.Config.LineSpacing = spacing
		}
	case 10: // 朗读速度
		input := showInputPrompt("请输入朗读速度 (1-10): ")
		if speed, err := strconv.Atoi(input); err == nil && speed >= 1 && speed <= 10 {
			r.Config.TTSSpeed = speed
		}
	case 11: // 自动朗读
		r.Config.AutoReadAloud = !r.Config.AutoReadAloud
	case 12: // 自动翻页间隔
        input := showInputPrompt("请输入自动翻页间隔(秒): ")
        if interval, err := strconv.Atoi(input); err == nil && interval > 0 {
            r.Config.AutoFlipInterval = interval
        } else {
            // 如果输入无效，设置为默认值
            r.Config.AutoFlipInterval = 5
        }
        // 保存配置
        saveConfig(r.Config)
    case 13: // 自动翻页
        r.Config.AutoFlipEnabled = !r.Config.AutoFlipEnabled
        // 如果启用自动翻页，确保有合理的间隔
        if r.Config.AutoFlipEnabled && r.Config.AutoFlipInterval <= 0 {
            r.Config.AutoFlipInterval = 5
        }
        // 保存配置
        saveConfig(r.Config)
        // 根据设置启动或停止自动翻页
        if r.Config.AutoFlipEnabled {
            r.startAutoFlip()
        } else {
            r.stopAutoFlip()
        }
    case 14: // 阅读提醒间隔
        input := showInputPrompt("请输入阅读提醒间隔(分钟，0表示不提醒): ")
        if interval, err := strconv.Atoi(input); err == nil && interval >= 0 {
            r.Config.RemindInterval = interval
            // 根据设置启动或停止提醒计时器
            if r.Config.RemindInterval > 0 {
                r.startRemindTimer()
            } else {
                r.stopRemindTimer()
            }
        }
    case 15: // 保存并退出
		saveConfig(r.Config)
		r.IsInSetting = false
	}
}

func (r *Reader) ShowHelp() {
    clearScreen()
    
    helpLines := []string{
        "快捷键帮助:",
        "========================================",
        "上/左/空格: 上一页",
        "下/右: 下一页",
        "s: 打开设置",
        "h: 打开帮助",
        "f: 打开书签",
        "b: 收藏/取消收藏",
        "/: 搜索",
        "r: 朗读/取消朗读",
        "q: 退出",
        "i: 隐藏/显示窗口",
        "g: 跳转到书签",
        "l: 跳转到页码",
        "n: 下一个搜索结果",
        "p: 上一个搜索结果",
        "t: 添加笔记",
        "v: 查看笔记",
        "e: 导出数据",
        "x: 查看阅读统计",
        "a: 自动翻页/取消自动翻页", // 新增自动翻页快捷键
        "ESC: 返回",
        "",
        "支持格式: TXT, EPUB, PDF, MOBI",
        "",
        "按任意键继续...",
    }
    
    // 计算居中位置
    _, height, _ := getTerminalSize()
    startY := (height - len(helpLines)) / 2
    
    for i, line := range helpLines {
        x := 2
        y := startY + i
        if y >= 0 && y < height {
            displayText(x, y, line, r.Config.FontColor, r.Config.BgColor)
        }
    }
    
    // 等待按键
    getInput()
}

// ShowBookmarks 显示书签
func (r *Reader) ShowBookmarks() {
    r.IsInBookmark = true
    
    if len(r.Bookmarks) == 0 {
        clearScreen()
        displayText(2, 2, "没有书签", r.Config.FontColor, r.Config.BgColor)
        displayText(2, 4, "按任意键继续...", r.Config.FontColor, r.Config.BgColor)
        getInput()
        r.IsInBookmark = false
        return
    }

    selected := 0
    for r.IsInBookmark {
        clearScreen()
        
        // 获取终端大小
        width, height, _ := getTerminalSize()
        
        // 显示标题
        title := "书签列表 - 使用上下键选择，回车键跳转，d键删除，ESC退出"
        displayText((width-len(title))/2, 2, title, r.Config.FontColor, r.Config.BgColor)
        
        // 显示分隔线
        separator := strings.Repeat("=", width-4)
        displayText(2, 3, separator, r.Config.FontColor, r.Config.BgColor)
        
        // 计算可显示的书签数量
        maxItems := height - 6
        startIdx := 0
        if selected >= maxItems {
            startIdx = selected - maxItems + 1
        }
        
        endIdx := startIdx + maxItems
        if endIdx > len(r.Bookmarks) {
            endIdx = len(r.Bookmarks)
        }
        
        // 显示书签列表
        for i := startIdx; i < endIdx; i++ {
            bookmark := r.Bookmarks[i]
            label := bookmark.Label
            if label == "" {
                label = fmt.Sprintf("第%d页", bookmark.Page+1)
            }
            
            y := 5 + (i - startIdx)
            if i == selected {
                displayText(4, y, "> "+label, r.Config.FontColor, r.Config.BgColor)
            } else {
                displayText(4, y, "  "+label, r.Config.FontColor, r.Config.BgColor)
            }
            
            // 显示文件名
            fileName := filepath.Base(bookmark.File)
            if len(fileName) > 20 {
                fileName = fileName[:17] + "..."
            }
            displayText(width-24, y, fileName, r.Config.FontColor, r.Config.BgColor)
        }
        
        // 显示滚动提示
        if startIdx > 0 {
            displayText(2, 5, "↑ 更多...", r.Config.FontColor, r.Config.BgColor)
        }
        if endIdx < len(r.Bookmarks) {
            displayText(2, height-2, "↓ 更多...", r.Config.FontColor, r.Config.BgColor)
        }

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
            if selected < len(r.Bookmarks)-1 {
                selected++
            }
        case "enter":
            r.CurrentPage = r.Bookmarks[selected].Page
            r.IsInBookmark = false
            return
        case "d":
            // 删除书签
            r.Bookmarks = append(r.Bookmarks[:selected], r.Bookmarks[selected+1:]...)
            saveBookmarks(r.FilePath, r.Bookmarks)
            if len(r.Bookmarks) == 0 {
                r.IsInBookmark = false
                return
            }
            if selected >= len(r.Bookmarks) {
                selected = len(r.Bookmarks) - 1
            }
        case "esc":
            r.IsInBookmark = false
            return
        }
    }
}


// ToggleBookmark 切换书签状态
func (r *Reader) ToggleBookmark() {
	// 检查当前页是否已经有书签
	for i, bookmark := range r.Bookmarks {
		if bookmark.Page == r.CurrentPage {
			// 删除书签
			r.Bookmarks = append(r.Bookmarks[:i], r.Bookmarks[i+1:]...)
			saveBookmarks(r.FilePath, r.Bookmarks)
			return
		}
	}

	// 添加新书签
	label := showInputPrompt("请输入书签名称 (直接回车使用默认名称): ")
	if label == "" {
		label = fmt.Sprintf("第%d页", r.CurrentPage+1)
	}

	newBookmark := Bookmark{
		File:  r.FilePath,
		Page:  r.CurrentPage,
		Label: label,
	}

	r.Bookmarks = append(r.Bookmarks, newBookmark)
	saveBookmarks(r.FilePath, r.Bookmarks)
}

// StartSearch 开始搜索
func (r *Reader) StartSearch() {
    r.IsInSearch = true
    
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
    term, _ := reader.ReadString('\n')
    term = strings.TrimSpace(term)
    
    if term == "" {
        r.IsInSearch = false
        return
    }

    r.SearchTerm = term
    r.SearchResults = []int{}

    // 在所有页面中搜索关键词
    for i, page := range r.Content {
        if strings.Contains(page, term) {
            r.SearchResults = append(r.SearchResults, i)
        }
    }

    if len(r.SearchResults) == 0 {
        clearScreen()
        fmt.Println("未找到匹配结果")
        fmt.Println("\n按任意键继续...")
        getInput()
        r.IsInSearch = false
        r.SearchTerm = ""
        return
    }

    r.CurrentSearch = 0
    r.CurrentPage = r.SearchResults[r.CurrentSearch]
}

// ToggleReadAloud 切换朗读状态
func (r *Reader) ToggleReadAloud() {
    if r.CurrentTTS.IsPlaying() {
        r.CurrentTTS.Stop()
    } else {
        // 朗读当前页内容
        if r.CurrentPage < len(r.Content) {
            text := r.Content[r.CurrentPage]
            // 限制文本长度，避免TTS命令过长
            if len(text) > 1000 {
                text = text[:1000] + "..."
            }
            r.CurrentTTS.PlayText(text, r.Config.TTSSpeed)
        }
    }
}

// HideWindow 隐藏/显示窗口
func (r *Reader) HideWindow() {
    if isWindowHidden {
        showWindow()
        isWindowHidden = false
    } else {
        hideWindow()
        isWindowHidden = true
    }
}

// GoToBookmark 跳转到书签
func (r *Reader) GoToBookmark() {
	if len(r.Bookmarks) == 0 {
		fmt.Println("没有书签")
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}

	// 显示书签列表并跳转
	r.ShowBookmarks()
}

// GoToPage 跳转到指定页码
func (r *Reader) GoToPage() {
	input := showInputPrompt("请输入页码: ")
	if page, err := strconv.Atoi(input); err == nil && page > 0 && page <= r.TotalPages {
		r.CurrentPage = page - 1
	}
}

// NextSearchResult 下一个搜索结果
func (r *Reader) NextSearchResult() {
	if len(r.SearchResults) == 0 {
		return
	}

	r.CurrentSearch = (r.CurrentSearch + 1) % len(r.SearchResults)
	r.CurrentPage = r.SearchResults[r.CurrentSearch]
}

// PreviousSearchResult 上一个搜索结果
func (r *Reader) PreviousSearchResult() {
	if len(r.SearchResults) == 0 {
		return
	}

	r.CurrentSearch = (r.CurrentSearch - 1 + len(r.SearchResults)) % len(r.SearchResults)
	r.CurrentPage = r.SearchResults[r.CurrentSearch]
}

// ClearSearch 清除搜索
func (r *Reader) ClearSearch() {
	r.SearchTerm = ""
	r.SearchResults = nil
	r.CurrentSearch = 0
}

// AddNote 添加笔记
func (r *Reader) AddNote() {
    if r.CurrentPage >= len(r.Content) {
        return
    }

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
    fmt.Print("请输入笔记内容: ")
    
    reader := bufio.NewReader(os.Stdin)
    noteContent, _ := reader.ReadString('\n')
    noteContent = strings.TrimSpace(noteContent)
    
    if noteContent == "" {
        return
    }

    // 创建新笔记
    newNote := Note{
        File:    r.FilePath,
        Page:    r.CurrentPage,
        Content: noteContent,
    }

    // 添加到笔记列表
    r.Notes = append(r.Notes, newNote)

    // 保存笔记
    saveNotes(r.FilePath, r.Notes)

    // 显示保存成功消息
    clearScreen()
    fmt.Println("笔记已保存")
    time.Sleep(1 * time.Second) // 显示消息1秒
}

// ShowNotes 显示笔记列表
func (r *Reader) ShowNotes() {
    if len(r.Notes) == 0 {
        clearScreen()
        fmt.Println("没有笔记")
        fmt.Println("\n按任意键继续...")
        getInput()
        return
    }

    selected := 0
    for {
        clearScreen()
        
        // 获取终端大小
        width, height, _ := getTerminalSize()
        
        // 显示标题
        title := "笔记列表 - 使用上下键选择，回车键查看，d键删除，ESC退出"
        displayText((width-len(title))/2, 2, title, r.Config.FontColor, r.Config.BgColor)
        displayText(2, 3, strings.Repeat("=", width-4), r.Config.FontColor, r.Config.BgColor)
        
        // 计算可显示的笔记数量
        maxItems := height - 6
        startIdx := 0
        if selected >= maxItems {
            startIdx = selected - maxItems + 1
        }
        
        endIdx := startIdx + maxItems
        if endIdx > len(r.Notes) {
            endIdx = len(r.Notes)
        }
        
        // 显示笔记列表
        for i := startIdx; i < endIdx; i++ {
            note := r.Notes[i]
            // 显示笔记预览
            preview := note.Content
            if len(preview) > 50 {
                preview = preview[:50] + "..."
            }
            
            line := fmt.Sprintf("第%d页: %s", note.Page+1, preview)
            y := 5 + (i - startIdx)
            
            if i == selected {
                displayText(4, y, "> "+line, r.Config.FontColor, r.Config.BgColor)
            } else {
                displayText(4, y, "  "+line, r.Config.FontColor, r.Config.BgColor)
            }
        }
        
        // 显示滚动提示
        if startIdx > 0 {
            displayText(2, 5, "↑ 更多...", r.Config.FontColor, r.Config.BgColor)
        }
        if endIdx < len(r.Notes) {
            displayText(2, height-2, "↓ 更多...", r.Config.FontColor, r.Config.BgColor)
        }

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
            if selected < len(r.Notes)-1 {
                selected++
            }
        case "enter":
            // 查看笔记详情
            clearScreen()
            title := fmt.Sprintf("笔记详情 (第%d页):", r.Notes[selected].Page+1)
            displayText((width-len(title))/2, 2, title, r.Config.FontColor, r.Config.BgColor)
            displayText(2, 3, strings.Repeat("=", width-4), r.Config.FontColor, r.Config.BgColor)
            
            // 显示笔记内容，自动换行
            lines := wrapText(r.Notes[selected].Content, width-4)
            for i, line := range lines {
                if i+5 >= height {
                    break
                }
                displayText(2, 5+i, line, r.Config.FontColor, r.Config.BgColor)
            }
            
            displayText(2, height-2, "按任意键返回...", r.Config.FontColor, r.Config.BgColor)
            getInput()
        case "d":
            // 删除笔记
            r.Notes = append(r.Notes[:selected], r.Notes[selected+1:]...)
            saveNotes(r.FilePath, r.Notes)
            if len(r.Notes) == 0 {
                return
            }
            if selected >= len(r.Notes) {
                selected = len(r.Notes) - 1
            }
        case "esc":
            return
        }
    }
}

// ShowReadingStats 显示阅读统计
func (r *Reader) ShowReadingStats() {
    clearScreen()
    
    // 获取终端大小
    width, height, _ := getTerminalSize()
    
    // 显示标题
    title := "阅读统计:"
    displayText((width-len(title))/2, 2, title, r.Config.FontColor, r.Config.BgColor)
    displayText(2, 3, strings.Repeat("=", width-4), r.Config.FontColor, r.Config.BgColor)
    
    // 计算阅读时间
    hours := r.ReadingStats.TotalReadingTime / 3600
    minutes := (r.ReadingStats.TotalReadingTime % 3600) / 60
    seconds := r.ReadingStats.TotalReadingTime % 60

    // 显示统计信息
    stats := []string{
        fmt.Sprintf("总阅读时间: %d小时%d分钟%d秒", hours, minutes, seconds),
        fmt.Sprintf("已读页数: %d", r.ReadingStats.PagesRead),
        fmt.Sprintf("已完成书籍: %d", r.ReadingStats.BooksCompleted),
    }
    
    // 显示最后阅读时间
    if r.ReadingStats.LastReadTime > 0 {
        lastRead := time.Unix(r.ReadingStats.LastReadTime, 0)
        stats = append(stats, fmt.Sprintf("最后阅读时间: %s", lastRead.Format("2006-01-02 15:04:05")))
    }
    
    // 显示统计信息
    for i, stat := range stats {
        if i+5 < height {
            displayText(2, 5+i, stat, r.Config.FontColor, r.Config.BgColor)
        }
    }
    
    displayText(2, height-2, "按任意键继续...", r.Config.FontColor, r.Config.BgColor)
    getInput()
}

// ExportData 导出功能
func (r *Reader) ExportData() {
    selected := 0
    options := []string{
        "导出书签",
        "导出笔记",
        "导出阅读统计",
        "返回",
    }
    
    for {
        clearScreen()
        
        // 获取终端大小
        width, height, _ := getTerminalSize()
        
        // 显示标题
        title := "导出数据:"
        displayText((width-len(title))/2, 2, title, r.Config.FontColor, r.Config.BgColor)
        displayText(2, 3, strings.Repeat("=", width-4), r.Config.FontColor, r.Config.BgColor)
        
        // 计算居中位置
        startY := (height - len(options) - 3) / 2
        
        // 显示选项
        for i, option := range options {
            y := startY + i
            if i == selected {
                displayText((width-len(option))/2, y, "> "+option, r.Config.FontColor, r.Config.BgColor)
            } else {
                displayText((width-len(option))/2, y, "  "+option, r.Config.FontColor, r.Config.BgColor)
            }
        }
        
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
            switch selected {
            case 0:
                r.exportBookmarks()
            case 1:
                r.exportNotes()
            case 2:
                r.exportStats()
            case 3:
                return
            }
        case "esc":
            return
        }
    }
}

// exportBookmarks 导出书签
func (r *Reader) exportBookmarks() {
	if len(r.Bookmarks) == 0 {
		fmt.Println("没有书签可导出")
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}

	// 获取导出路径
	exportPath := showInputPrompt("请输入导出路径 (默认: ./bookmarks.csv): ")
	if exportPath == "" {
		exportPath = "./bookmarks.csv"
	}

	// 创建CSV文件
	file, err := os.Create(exportPath)
	if err != nil {
		fmt.Printf("创建文件失败: %v\n", err)
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}
	defer file.Close()

	// 创建CSV writer
	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	writer.Write([]string{"文件", "页码", "标签"})

	// 写入书签数据
	for _, bookmark := range r.Bookmarks {
		writer.Write([]string{
			bookmark.File,
			strconv.Itoa(bookmark.Page + 1),
			bookmark.Label,
		})
	}

	fmt.Printf("书签已导出到: %s\n", exportPath)
	fmt.Println("\n按任意键继续...")
	getInput()
}

// exportNotes 导出笔记
func (r *Reader) exportNotes() {
	if len(r.Notes) == 0 {
		fmt.Println("没有笔记可导出")
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}

	// 获取导出路径
	exportPath := showInputPrompt("请输入导出路径 (默认: ./notes.csv): ")
	if exportPath == "" {
		exportPath = "./notes.csv"
	}

	// 创建CSV文件
	file, err := os.Create(exportPath)
	if err != nil {
		fmt.Printf("创建文件失败: %v\n", err)
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}
	defer file.Close()

	// 创建CSV writer
	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	writer.Write([]string{"文件", "页码", "内容"})

	// 写入笔记数据
	for _, note := range r.Notes {
		writer.Write([]string{
			note.File,
			strconv.Itoa(note.Page + 1),
			note.Content,
		})
	}

	fmt.Printf("笔记已导出到: %s\n", exportPath)
	fmt.Println("\n按任意键继续...")
	getInput()
}

// exportStats 导出阅读统计
func (r *Reader) exportStats() {
	// 获取导出路径
	exportPath := showInputPrompt("请输入导出路径 (默认: ./stats.csv): ")
	if exportPath == "" {
		exportPath = "./stats.csv"
	}

	// 创建CSV文件
	file, err := os.Create(exportPath)
	if err != nil {
		fmt.Printf("创建文件失败: %v\n", err)
		fmt.Println("\n按任意键继续...")
		getInput()
		return
	}
	defer file.Close()

	// 创建CSV writer
	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	writer.Write([]string{"文件", "总阅读时间(秒)", "已读页数", "已完成书籍", "最后阅读时间"})

	// 计算阅读时间
	hours := r.ReadingStats.TotalReadingTime / 3600
	minutes := (r.ReadingStats.TotalReadingTime % 3600) / 60
	seconds := r.ReadingStats.TotalReadingTime % 60
	readingTimeStr := fmt.Sprintf("%d小时%d分钟%d秒", hours, minutes, seconds)

	// 格式化最后阅读时间
	lastReadTime := ""
	if r.ReadingStats.LastReadTime > 0 {
		lastRead := time.Unix(r.ReadingStats.LastReadTime, 0)
		lastReadTime = lastRead.Format("2006-01-02 15:04:05")
	}

	// 写入统计数据
	writer.Write([]string{
		r.FilePath,
		readingTimeStr,
		strconv.Itoa(r.ReadingStats.PagesRead),
		strconv.Itoa(r.ReadingStats.BooksCompleted),
		lastReadTime,
	})

	fmt.Printf("统计已导出到: %s\n", exportPath)
	fmt.Println("\n按任意键继续...")
	getInput()
}

// updateReadingStats 更新阅读统计
func (r *Reader) updateReadingStats(startTime int64) {
    currentTime := time.Now().Unix()
    r.ReadingStats.TotalReadingTime += currentTime - startTime
    r.ReadingStats.PagesRead = r.CurrentPage // 更新已读页数为当前页
    r.ReadingStats.LastReadTime = currentTime
    r.ReadingStats.LastPage = r.CurrentPage // 记录最后阅读位置

    // 如果读完了整本书，增加已完成书籍计数
    if r.CurrentPage >= r.TotalPages-1 {
        r.ReadingStats.BooksCompleted++
    }

    // 保存阅读统计
    saveReadingStats(r.FilePath, r.ReadingStats)
}

// highlightSearchTerms 高亮搜索词
func (r *Reader) highlightSearchTerms() {
	// 实现搜索词高亮
	// 这需要在渲染时特殊处理，比较复杂，暂时不实现
}

func loadBookmarksForFile(filePath string) []Bookmark {
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

	var allBookmarks []Bookmark
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&allBookmarks); err != nil {
		return []Bookmark{}
	}

	// 过滤出当前文件的书签
	var fileBookmarks []Bookmark
	for _, bookmark := range allBookmarks {
		if bookmark.File == filePath {
			fileBookmarks = append(fileBookmarks, bookmark)
		}
	}

	return fileBookmarks
}

func saveBookmarks(filePath string, bookmarks []Bookmark) error {
	bookmarksPath := getBookmarksPath()

	// 确保目录存在
	bookmarksDir := filepath.Dir(bookmarksPath)
	if err := os.MkdirAll(bookmarksDir, 0755); err != nil {
		return err
	}

	// 读取所有书签
	var allBookmarks []Bookmark
	if _, err := os.Stat(bookmarksPath); !os.IsNotExist(err) {
		file, err := os.Open(bookmarksPath)
		if err == nil {
			defer file.Close()
			decoder := json.NewDecoder(file)
			decoder.Decode(&allBookmarks)
		}
	}

	// 移除当前文件的所有书签
	var newBookmarks []Bookmark
	for _, bookmark := range allBookmarks {
		if bookmark.File != filePath {
			newBookmarks = append(newBookmarks, bookmark)
		}
	}

	// 添加当前文件的新书签
	newBookmarks = append(newBookmarks, bookmarks...)

	// 保存书签
	file, err := os.Create(bookmarksPath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(newBookmarks)
}

func loadNotes(filePath string) []Note {
	notesPath := getNotesPath()

	// 如果笔记文件不存在，返回空列表
	if _, err := os.Stat(notesPath); os.IsNotExist(err) {
		return []Note{}
	}

	// 读取笔记文件
	file, err := os.Open(notesPath)
	if err != nil {
		return []Note{}
	}
	defer file.Close()

	var allNotes map[string][]Note
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&allNotes); err != nil {
		return []Note{}
	}

	// 返回当前文件的笔记
	return allNotes[filePath]
}

func saveNotes(filePath string, notes []Note) error {
	notesPath := getNotesPath()

	// 确保目录存在
	notesDir := filepath.Dir(notesPath)
	if err := os.MkdirAll(notesDir, 0755); err != nil {
		return err
	}

	// 读取所有笔记
	var allNotes map[string][]Note
	if _, err := os.Stat(notesPath); !os.IsNotExist(err) {
		file, err := os.Open(notesPath)
		if err == nil {
			defer file.Close()
			decoder := json.NewDecoder(file)
			decoder.Decode(&allNotes)
		}
	}

	if allNotes == nil {
		allNotes = make(map[string][]Note)
	}

	// 更新当前文件的笔记
	allNotes[filePath] = notes

	// 保存笔记
	file, err := os.Create(notesPath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(allNotes)
}

// loadReadingStats 加载阅读统计
func loadReadingStats(filePath string) *ReadingStats {
    statsPath := getStatsPath()

    // 如果统计文件不存在，返回空统计
    if _, err := os.Stat(statsPath); os.IsNotExist(err) {
        return &ReadingStats{}
    }

    // 读取统计文件
    file, err := os.Open(statsPath)
    if err != nil {
        return &ReadingStats{}
    }
    defer file.Close()

    var allStats map[string]*ReadingStats
    decoder := json.NewDecoder(file)
    if err := decoder.Decode(&allStats); err != nil {
        return &ReadingStats{}
    }

    // 返回当前文件的统计
    if stats, exists := allStats[filePath]; exists {
        return stats
    }

    return &ReadingStats{}
}

// saveReadingStats 保存阅读统计
func saveReadingStats(filePath string, stats *ReadingStats) error {
    statsPath := getStatsPath()

    // 确保目录存在
    statsDir := filepath.Dir(statsPath)
    if err := os.MkdirAll(statsDir, 0755); err != nil {
        return err
    }

    // 读取所有统计
    var allStats map[string]*ReadingStats
    if _, err := os.Stat(statsPath); !os.IsNotExist(err) {
        file, err := os.Open(statsPath)
        if err == nil {
            defer file.Close()
            decoder := json.NewDecoder(file)
            decoder.Decode(&allStats)
        }
    }

    if allStats == nil {
        allStats = make(map[string]*ReadingStats)
    }

    // 更新当前文件的统计
    allStats[filePath] = stats

    // 保存统计
    file, err := os.Create(statsPath)
    if err != nil {
        return err
    }
    defer file.Close()

    encoder := json.NewEncoder(file)
    encoder.SetIndent("", "  ")
    return encoder.Encode(allStats)
}


func getBookmarksPath() string {
	homeDir, _ := os.UserHomeDir()
	return filepath.Join(homeDir, ".config", "novel-reader", "bookmarks.json")
}

func getNotesPath() string {
	homeDir, _ := os.UserHomeDir()
	return filepath.Join(homeDir, ".config", "novel-reader", "notes.json")
}

func getStatsPath() string {
	homeDir, _ := os.UserHomeDir()
	return filepath.Join(homeDir, ".config", "novel-reader", "stats.json")
}

func getFileName(path string) string {
	return filepath.Base(path)
}

// startAutoFlip 启动自动翻页
func (r *Reader) startAutoFlip() {
    // 如果已经启动，先停止
    r.stopAutoFlip()
    
    // 确保间隔大于0
    interval := r.Config.AutoFlipInterval
    if interval <= 0 {
        interval = 5 // 默认5秒
        r.Config.AutoFlipInterval = interval
    }
    
    // 创建计时器和退出通道
    r.AutoFlipTicker = time.NewTicker(time.Duration(interval) * time.Second)
    r.AutoFlipQuit = make(chan struct{})
    
    // 启动goroutine处理自动翻页
    go func() {
        for {
            select {
            case <-r.AutoFlipTicker.C:
                // 如果不是最后一页，翻到下一页
                if r.CurrentPage < r.TotalPages-1 {
                    r.CurrentPage++
                    r.RenderPage()
                } else {
                    // 如果是最后一页，停止自动翻页
                    r.stopAutoFlip()
                    r.Config.AutoFlipEnabled = false
                    saveConfig(r.Config)
                }
            case <-r.AutoFlipQuit:
                if r.AutoFlipTicker != nil {
                    r.AutoFlipTicker.Stop()
                }
                return
            }
        }
    }()
    
    r.Config.AutoFlipEnabled = true
}

// stopAutoFlip 停止自动翻页
func (r *Reader) stopAutoFlip() {
    if r.AutoFlipQuit != nil {
        close(r.AutoFlipQuit)
        r.AutoFlipQuit = nil
    }
    if r.AutoFlipTicker != nil {
        r.AutoFlipTicker.Stop()
        r.AutoFlipTicker = nil
    }
    r.Config.AutoFlipEnabled = false
    fmt.Println("自动翻页已停止")
}

// toggleAutoFlip 切换自动翻页状态
func (r *Reader) toggleAutoFlip() {
	if r.Config.AutoFlipEnabled {
		r.stopAutoFlip()
	} else {
		r.startAutoFlip()
	}
}

// startRemindTimer 启动提醒计时器
func (r *Reader) startRemindTimer() {
    // 如果已经启动，先停止
    r.stopRemindTimer()
    
    interval := time.Duration(r.Config.RemindInterval) * time.Minute
    if interval <= 0 {
        return
    }
    
    // 创建计时器和退出通道
    r.RemindTicker = time.NewTicker(interval)
    r.RemindQuit = make(chan struct{})
    
    // 启动goroutine处理提醒
    go func() {
        for {
            select {
            case <-r.RemindTicker.C:
                r.showRemindAlert()
            case <-r.RemindQuit:
                if r.RemindTicker != nil {
                    r.RemindTicker.Stop()
                }
                return
            }
        }
    }()
}

// stopRemindTimer 停止提醒计时器
func (r *Reader) stopRemindTimer() {
    if r.RemindQuit != nil {
        close(r.RemindQuit)
        r.RemindQuit = nil
    }
    if r.RemindTicker != nil {
        r.RemindTicker.Stop()
        r.RemindTicker = nil
    }
}

// showRemindAlert 显示提醒弹窗
func (r *Reader) showRemindAlert() {
    // 恢复终端状态以显示提醒
    if oldState != nil {
        term.Restore(int(os.Stdin.Fd()), oldState)
    }
    
    defer func() {
        // 恢复原始模式
        if oldState != nil {
            term.MakeRaw(int(os.Stdin.Fd()))
        }
        // 重新渲染页面
        r.RenderPage()
    }()
    
    clearScreen()
    
    // 获取终端大小
    width, height, _ := getTerminalSize()
    
    // 计算弹窗位置和大小
    popupWidth := 50
    popupHeight := 7
    popupX := (width - popupWidth) / 2
    popupY := (height - popupHeight) / 2
    
    // 绘制弹窗边框
    drawPopup(popupX, popupY, popupWidth, popupHeight, r.Config.BorderStyle)
    
    // 显示提醒消息
    message := fmt.Sprintf("已经阅读%d分钟了,休息会眼睛吧!", r.Config.RemindInterval)
    messageX := popupX + (popupWidth-len(message))/2
    displayText(messageX, popupY+2, message, r.Config.FontColor, r.Config.BgColor)
    
    // 显示确认提示
    prompt := "按任意键继续阅读..."
    promptX := popupX + (popupWidth-len(prompt))/2
    displayText(promptX, popupY+4, prompt, r.Config.FontColor, r.Config.BgColor)
    
    // 等待按键
    getInput()
    
    // 重置提醒计时器
    r.stopRemindTimer()
    r.startRemindTimer()
}

// drawPopup 绘制弹窗
func drawPopup(x, y, width, height int, style string) {
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
    default:
        return // 无边框
    }

    // 绘制上边框
    fmt.Printf("\033[%d;%dH%s", y+1, x+1, topLeft)
    for i := 0; i < width-2; i++ {
        fmt.Print(horizontal)
    }
    fmt.Print(topRight)

    // 绘制左右边框
    for i := 1; i < height-1; i++ {
        fmt.Printf("\033[%d;%dH%s", y+i+1, x+1, vertical)
        fmt.Printf("\033[%d;%dH%s", y+i+1, x+width, vertical)
    }

    // 绘制下边框
    fmt.Printf("\033[%d;%dH%s", y+height, x+1, bottomLeft)
    for i := 0; i < width-2; i++ {
        fmt.Print(horizontal)
    }
    fmt.Print(bottomRight)
}

./tui.go
\n=======================\n
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

以下是greader命令的代码:
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
	fmt.Fprintf(os.Stderr, "Detected encoding: %s\n", encoding)
	fmt.Fprintf(os.Stderr, "File size: %d bytes\n", len(content))

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

	fmt.Fprintf(os.Stderr, "Converted content size: %d characters\n", len(utf8Content))
	
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
	fmt.Fprintf(os.Stderr, "Content preview: %s\n", string(utf8Content[:previewLength]))

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

	fmt.Fprintf(os.Stderr, "Rows per page: %d, Total lines: %d\n", rowsPerPage, len(lines))

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
	
	fmt.Fprintf(os.Stderr, "Total pages: %d\n", nr.totalPages)
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

其中reader命令的在终端中直接使用效果更好, greader命令在fzf、其他脚本或命令调用的时候效果更好一些,
目前我在终端直接使用reader命令, 而fzf、其他脚本或命令调用的时候使用greader, 这样我要维护两套代码, 太麻烦了,
我想把这两套代码整合为一套, 使其可以在各种环境下都非常好用.
既要将所有的功能保留下来, 又要有出色的使用表现;
本项目在此种情况下诞生, 目前处于开发阶段;