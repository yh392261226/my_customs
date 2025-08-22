package core

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
	b.content = ProcessContent(allContent, 80, 24, 1, 1)

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

	return ProcessContent(content, 80, 24, 1, 1), nil
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