package ui

import (
	"os"

	"golang.org/x/term"
)

// getTerminalSize 获取终端大小
func getTerminalSize() (int, int, error) {
    if !term.IsTerminal(int(os.Stdout.Fd())) {
        return 80, 24, nil
    }
    
    width, height, err := term.GetSize(int(os.Stdout.Fd()))
    if err != nil {
        return 80, 24, err
    }
    
    return width, height, nil
}