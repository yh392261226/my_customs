package config

import (
	"encoding/json"
	"os"
	"path/filepath"
)

// ReadingProgress 阅读进度
type ReadingProgress struct {
	FilePath   string `json:"file_path"`
	LastPage   int    `json:"last_page"`
	TotalPages int    `json:"total_pages"`
}

// LoadProgress 加载阅读进度
func LoadProgress(filePath string) *ReadingProgress {
	progressPath := getProgressPath()
	if _, err := os.Stat(progressPath); os.IsNotExist(err) {
		return &ReadingProgress{}
	}

	file, err := os.Open(progressPath)
	if err != nil {
		return &ReadingProgress{}
	}
	defer file.Close()

	var progress map[string]*ReadingProgress
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&progress); err != nil {
		return &ReadingProgress{}
	}

	if p, exists := progress[filePath]; exists {
		return p
	}

	return &ReadingProgress{}
}

// SaveProgress 保存阅读进度
func SaveProgress(progress *ReadingProgress) error {
	progressPath := getProgressPath()
	progressDir := filepath.Dir(progressPath)
	if err := os.MkdirAll(progressDir, 0755); err != nil {
		return err
	}

	// 读取所有进度
	var allProgress map[string]*ReadingProgress
	if _, err := os.Stat(progressPath); !os.IsNotExist(err) {
		file, err := os.Open(progressPath)
		if err == nil {
			defer file.Close()
			decoder := json.NewDecoder(file)
			decoder.Decode(&allProgress)
		}
	}

	if allProgress == nil {
		allProgress = make(map[string]*ReadingProgress)
	}

	// 更新当前文件的进度
	allProgress[progress.FilePath] = progress

	// 保存进度
	file, err := os.Create(progressPath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(allProgress)
}

func getProgressPath() string {
	homeDir, _ := os.UserHomeDir()
	return filepath.Join(homeDir, ".config", "unified-reader", "progress.json")
}