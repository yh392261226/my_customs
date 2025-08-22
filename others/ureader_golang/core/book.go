package core

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
)

// BookType 书籍类型
type BookType int

const (
	BookTypeTXT BookType = iota
	BookTypeEPUB
	BookTypePDF
	BookTypeMOBI
	BookTypeUnknown
)

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
	Genre       string   `json:"genre"`
}

// Book 书籍接口
type Book interface {
	GetMetadata() *BookMetadata
	GetContent() ([]string, error)
	GetChapter(index int) ([]string, error)
	GetCover() ([]byte, error)
	Close() error
}

// 根据文件扩展名检测书籍类型
func DetectBookType(filePath string) BookType {
	ext := strings.ToLower(filepath.Ext(filePath))
	switch ext {
	case ".txt":
		return BookTypeTXT
	case ".epub":
		return BookTypeEPUB
	case ".mobi", ".pdf", ".azw", ".azw3":
		// 暂时不支持这些格式
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

	bookType := DetectBookType(filePath)
	
	switch bookType {
	case BookTypeTXT:
		return NewTxtBook(filePath)
	case BookTypeEPUB:
		return NewEpubBook(filePath)
	default:
		return nil, errors.New("不支持的格式")
	}
}