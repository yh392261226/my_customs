package tts

import (
	"encoding/base64"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"unicode/utf8"
)

// TTSPlayer 文本转语音播放器
type TTSPlayer struct {
	cmd     *exec.Cmd
	mutex   sync.Mutex
	playing bool
	stopCh  chan struct{}
}

// NewTTSPlayer 创建新的TTS播放器
func NewTTSPlayer() *TTSPlayer {
	return &TTSPlayer{
		playing: false,
	}
}

// 添加TTS命令检查
func checkTTSCommand() error {
    if isLinux() {
        _, err := exec.LookPath("espeak")
        if err != nil {
            return fmt.Errorf("espeak未安装，请先安装: sudo apt-get install espeak")
        }
    } else if isWindows() {
        // 检查PowerShell是否可用
        _, err := exec.LookPath("powershell")
        if err != nil {
            return fmt.Errorf("PowerShell不可用")
        }
    }
    // macOS的say命令应该总是可用
    return nil
}

// PlayText 播放文本
func (t *TTSPlayer) PlayText(text string, speed int) error {
    t.mutex.Lock()
    defer t.mutex.Unlock()

    // 确保文本是 UTF-8 编码
    if !utf8.ValidString(text) {
        // 如果不是 UTF-8，尝试转换
        text = string([]rune(text)) // 转换为 rune 再转回 string
    }

    // 如果正在播放，先停止
    if t.playing {
        t.stopCh <- struct{}{}
        if t.cmd != nil && t.cmd.Process != nil {
            t.cmd.Process.Kill()
        }
        t.playing = false
    }

    // 根据操作系统选择不同的TTS命令
    var cmd *exec.Cmd
    if isLinux() {
        // Linux使用espeak，通过标准输入传递文本
        cmd = exec.Command("espeak", "-s", strconv.Itoa(speed*30))
        cmd.Stdin = strings.NewReader(text)
    } else if isMacOS() {
        // macOS使用say，通过标准输入传递文本
        rate := mapSpeedToRate(speed)
        cmd = exec.Command("say", "-r", rate)
        cmd.Stdin = strings.NewReader(text)
    } else if isWindows() {
        // Windows使用PowerShell的SpeechSynthesizer
        // 使用base64编码文本以避免特殊字符问题
        encodedText := base64.StdEncoding.EncodeToString([]byte(text))
        psScript := fmt.Sprintf(
            `Add-Type -AssemblyName System.Speech; 
             $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; 
             $speak.Rate = %d; 
             $bytes = [System.Convert]::FromBase64String('%s');
             $text = [System.Text.Encoding]::UTF8.GetString($bytes);
             $speak.Speak($text);`,
            (speed-5)*2,
            encodedText,
        )
        cmd = exec.Command("powershell", "-Command", psScript)
    } else {
        return fmt.Errorf("不支持的操作系统")
    }

    // 设置输出和错误
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr

    t.cmd = cmd
    t.playing = true
    t.stopCh = make(chan struct{}, 1)

    // 启动TTS进程
    go func() {
        err := cmd.Run()
        
        t.mutex.Lock()
        defer t.mutex.Unlock()
        
        // 检查是否是被主动停止的
        select {
        case <-t.stopCh:
            // 是被主动停止的，不更新状态
        default:
            t.playing = false
        }
        
        if err != nil && err.Error() != "signal: killed" {
            fmt.Printf("TTS错误: %v\n", err)
            // 输出更多调试信息
            fmt.Printf("命令: %s\n", strings.Join(cmd.Args, " "))
        }
    }()

    return nil
}

// isTTSAvailable 检查系统是否支持TTS
func isTTSAvailable() bool {
    if isLinux() {
        _, err := exec.LookPath("espeak")
        return err == nil
    } else if isMacOS() {
        // macOS的say命令应该总是可用
        return true
    } else if isWindows() {
        // 检查PowerShell是否可用
        _, err := exec.LookPath("powershell")
        return err == nil
    }
    return false
}

// Stop 停止播放
func (t *TTSPlayer) Stop() {
	t.mutex.Lock()
	defer t.mutex.Unlock()

	if t.playing {
		t.stopCh <- struct{}{}
		if t.cmd != nil && t.cmd.Process != nil {
			t.cmd.Process.Kill()
		}
		t.playing = false
	}
}

// IsPlaying 检查是否正在播放
func (t *TTSPlayer) IsPlaying() bool {
	t.mutex.Lock()
	defer t.mutex.Unlock()
	return t.playing
}

// 辅助函数：检测操作系统
func isLinux() bool {
	return strings.Contains(strings.ToLower(runtime.GOOS), "linux")
}

func isMacOS() bool {
	return strings.Contains(strings.ToLower(runtime.GOOS), "darwin")
}

func isWindows() bool {
	return strings.Contains(strings.ToLower(runtime.GOOS), "windows")
}

// 将速度值映射到macOS的语速范围
func mapSpeedToRate(speed int) string {
	// 将1-10的速度映射到150-300的语速范围
	rate := 150 + (speed-1)*15
	return strconv.Itoa(rate)
}