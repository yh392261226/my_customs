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