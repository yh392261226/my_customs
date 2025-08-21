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