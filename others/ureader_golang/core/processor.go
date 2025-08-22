package core

import (
	"regexp"
	"strings"

	"github.com/mattn/go-runewidth"
)

// processContent 处理内容，包括自动换行和分章
func ProcessContent(lines []string, width, height, margin, padding int) []string {
	var processedPages []string
	var currentPage strings.Builder
	currentLineLength := 0
	maxWidth := width - 2*margin - 2*padding
	maxHeight := height - 2*margin - 2*padding - 2 // 标题和进度条占用的行

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