package main

import (
	"bufio"
	"io"
	"os"
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
	
	// 对于大文件，使用缓冲读取器逐行读取
	var lines []string
	scanner := bufio.NewScanner(reader)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	
	if err := scanner.Err(); err != nil {
		return nil, err
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