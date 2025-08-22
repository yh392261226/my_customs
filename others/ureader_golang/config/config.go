package config

import (
	"encoding/json"
	"os"
	"path/filepath"
)

// Config 配置结构
type Config struct {
	FontColor       string `json:"font_color"`
    BackgroundColor string `json:"background_color"`
    BorderColor     string `json:"border_color"`
    BorderStyle     string `json:"border_style"`
    Width           int    `json:"width"`
    Height          int    `json:"height"`
    Margin          int    `json:"margin"`
    Padding         int    `json:"padding"`
    TTSSpeed        int    `json:"tts_speed"`
    AutoReadAloud   bool   `json:"auto_read_aloud"`
    AutoFlip        bool   `json:"auto_flip"`
    AutoFlipInterval int   `json:"auto_flip_interval"`
    ShowProgress    bool   `json:"show_progress"`
    RemindInterval  int    `json:"remind_interval"`
}

// LoadConfig 加载配置
func LoadConfig() *Config {
	configPath := getConfigPath()
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return defaultConfig()
	}

	file, err := os.Open(configPath)
	if err != nil {
		return defaultConfig()
	}
	defer file.Close()

	var config Config
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&config); err != nil {
		return defaultConfig()
	}

	return &config
}

// SaveConfig 保存配置
func SaveConfig(config *Config) error {
	configPath := getConfigPath()
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

func getConfigPath() string {
	homeDir, _ := os.UserHomeDir()
	return filepath.Join(homeDir, ".config", "unified-reader", "config.json")
}

func defaultConfig() *Config {
    return &Config{
        FontColor:       "white",
        BackgroundColor: "black",
        BorderColor:     "gray",
        BorderStyle:     "single",
        Width:           80,
        Height:          24,
        Margin:          1,
        Padding:         1,
        TTSSpeed:        5,
        AutoReadAloud:   false,
        AutoFlip:        false,
        AutoFlipInterval: 5, // 确保是正数
        ShowProgress:    true,
        RemindInterval:  30, // 确保是正数
    }
}