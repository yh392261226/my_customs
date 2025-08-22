package ui

// RunMode 运行模式
type RunMode int

const (
	ModeAuto RunMode = iota
	ModeRawTerminal
	ModeTUI
	ModeSimple
)