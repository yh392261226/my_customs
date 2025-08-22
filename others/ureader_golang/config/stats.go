package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"
)

// ReadingStats 阅读统计
type ReadingStats struct {
    TotalReadingTime time.Duration `json:"total_reading_time"`
    TotalPagesRead   int           `json:"total_pages_read"`
    TotalBooksRead   int           `json:"total_books_read"`
    DailyStats       map[string]DailyStat `json:"daily_stats"` // 日期 -> 每日统计
    BookStats        map[string]BookStat  `json:"book_stats"`  // 文件路径 -> 书籍统计
    GenrePreferences map[string]int       `json:"genre_preferences"` // 题材偏好
}

// DailyStat 每日统计
type DailyStat struct {
    Date          string        `json:"date"`
    ReadingTime   time.Duration `json:"reading_time"`
    PagesRead     int           `json:"pages_read"`
    BooksRead     int           `json:"books_read"`
}

// BookStat 书籍统计
type BookStat struct {
    FilePath      string        `json:"file_path"`
    Title         string        `json:"title"`
    TotalPages    int           `json:"total_pages"`
    PagesRead     int           `json:"pages_read"`
    ReadingTime   time.Duration `json:"reading_time"`
    CompletionRate float64      `json:"completion_rate"`
    LastRead      time.Time     `json:"last_read"`
    Genre         string        `json:"genre"`
}

// LoadStats 加载阅读统计
func LoadStats() *ReadingStats {
    statsPath := getStatsPath()
    if _, err := os.Stat(statsPath); os.IsNotExist(err) {
        return &ReadingStats{
            DailyStats:       make(map[string]DailyStat),
            BookStats:        make(map[string]BookStat),
            GenrePreferences: make(map[string]int),
        }
    }

    file, err := os.Open(statsPath)
    if err != nil {
        return &ReadingStats{
            DailyStats:       make(map[string]DailyStat),
            BookStats:        make(map[string]BookStat),
            GenrePreferences: make(map[string]int),
        }
    }
    defer file.Close()

    var stats ReadingStats
    decoder := json.NewDecoder(file)
    if err := decoder.Decode(&stats); err != nil {
        return &ReadingStats{
            DailyStats:       make(map[string]DailyStat),
            BookStats:        make(map[string]BookStat),
            GenrePreferences: make(map[string]int),
        }
    }

    return &stats
}

// SaveStats 保存阅读统计
func SaveStats(stats *ReadingStats) error {
    statsPath := getStatsPath()
    statsDir := filepath.Dir(statsPath)
    if err := os.MkdirAll(statsDir, 0755); err != nil {
        return err
    }

    file, err := os.Create(statsPath)
    if err != nil {
        return err
    }
    defer file.Close()

    encoder := json.NewEncoder(file)
    encoder.SetIndent("", "  ")
    return encoder.Encode(stats)
}

// UpdateReadingStats 更新阅读统计
func UpdateReadingStats(filePath, title string, pagesRead, totalPages int, readingTime time.Duration, genre string) {
    stats := LoadStats()
    
    // 更新总统计
    stats.TotalReadingTime += readingTime
    stats.TotalPagesRead += pagesRead
    
    // 更新每日统计
    today := time.Now().Format("2006-01-02")
    dailyStat, exists := stats.DailyStats[today]
    if !exists {
        dailyStat = DailyStat{Date: today}
    }
    dailyStat.ReadingTime += readingTime
    dailyStat.PagesRead += pagesRead
    stats.DailyStats[today] = dailyStat
    
    // 更新书籍统计
    bookStat, exists := stats.BookStats[filePath]
    if !exists {
        bookStat = BookStat{
            FilePath: filePath,
            Title:    title,
            TotalPages: totalPages,
        }
    }
    bookStat.PagesRead += pagesRead
    bookStat.ReadingTime += readingTime
    bookStat.CompletionRate = float64(bookStat.PagesRead) / float64(bookStat.TotalPages) * 100
    bookStat.LastRead = time.Now()
    bookStat.Genre = genre
    stats.BookStats[filePath] = bookStat
    
    // 更新题材偏好
    if genre != "" {
        stats.GenrePreferences[genre] += pagesRead
    }
    
    // 如果阅读完成，增加已读书籍计数
    if bookStat.PagesRead >= bookStat.TotalPages && !exists {
        stats.TotalBooksRead++
        dailyStat.BooksRead++
        stats.DailyStats[today] = dailyStat
    }
    
    SaveStats(stats)
}

func getStatsPath() string {
    homeDir, _ := os.UserHomeDir()
    return filepath.Join(homeDir, ".config", "unified-reader", "stats.json")
}