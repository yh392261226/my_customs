package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"
)

// Bookmark 书签结构
type Bookmark struct {
    FilePath    string    `json:"file_path"`
    Page        int       `json:"page"`
    Label       string    `json:"label"`
    CreatedAt   time.Time `json:"created_at"`
    UpdatedAt   time.Time `json:"updated_at"`
    IsFavorite  bool      `json:"is_favorite"` // 是否收藏
    Category    string    `json:"category"`    // 分类
}

// LoadBookmarks 加载书签
func LoadBookmarks() []*Bookmark {
	bookmarksPath := getBookmarksPath()
	if _, err := os.Stat(bookmarksPath); os.IsNotExist(err) {
		return []*Bookmark{}
	}

	file, err := os.Open(bookmarksPath)
	if err != nil {
		return []*Bookmark{}
	}
	defer file.Close()

	var bookmarks []*Bookmark
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&bookmarks); err != nil {
		return []*Bookmark{}
	}

	return bookmarks
}

// SaveBookmarks 保存书签
func SaveBookmarks(bookmarks []*Bookmark) error {
	bookmarksPath := getBookmarksPath()
	bookmarksDir := filepath.Dir(bookmarksPath)
	if err := os.MkdirAll(bookmarksDir, 0755); err != nil {
		return err
	}

	file, err := os.Create(bookmarksPath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(bookmarks)
}

// AddBookmark 添加书签
func AddBookmark(bookmark *Bookmark) error {
	bookmarks := LoadBookmarks()
	
	// 检查是否已存在
	for i, bm := range bookmarks {
		if bm.FilePath == bookmark.FilePath && bm.Page == bookmark.Page {
			// 更新标签
			bookmarks[i].Label = bookmark.Label
			return SaveBookmarks(bookmarks)
		}
	}
	
	// 添加新书签
	bookmarks = append(bookmarks, bookmark)
	return SaveBookmarks(bookmarks)
}

// RemoveBookmark 删除书签
func RemoveBookmark(filePath string, page int) error {
	bookmarks := LoadBookmarks()
	for i, bm := range bookmarks {
		if bm.FilePath == filePath && bm.Page == page {
			bookmarks = append(bookmarks[:i], bookmarks[i+1:]...)
			return SaveBookmarks(bookmarks)
		}
	}
	return nil
}

func getBookmarksPath() string {
	homeDir, _ := os.UserHomeDir()
	return filepath.Join(homeDir, ".config", "unified-reader", "bookmarks.json")
}