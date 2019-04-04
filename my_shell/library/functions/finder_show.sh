# Desc: 文件夹显示隐藏文件
function showF() { defaults write com.apple.Finder AppleShowAllFiles YES ; killall Finder /System/Library/CoreServices/Finder.app;}
