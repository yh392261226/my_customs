package core

import (
	"bufio"
	"io"
	"os"
	"unicode/utf8"

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
	
	// 使用 bufio.Reader 而不是 Scanner 来避免 "token too long" 错误
	bufReader := bufio.NewReader(reader)
	var lines []string
	
	for {
		line, err := bufReader.ReadString('\n')
		if err != nil && err != io.EOF {
			return nil, err
		}
		
		// 去除行尾的换行符
		if len(line) > 0 && line[len(line)-1] == '\n' {
			line = line[:len(line)-1]
		}
		if len(line) > 0 && line[len(line)-1] == '\r' {
			line = line[:len(line)-1]
		}
		
		lines = append(lines, line)
		
		if err == io.EOF {
			break
		}
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