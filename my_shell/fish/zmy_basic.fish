#我自己的一些配置
##设置一些变量
set -gx MYRUNTIME (cat ~/.myruntime)
set -gx MYPATH $MYRUNTIME
set -gx USERNAME json
set -gx GOPATH $HOME/go-develop
set -gx GOOS darwin
set -gx GOARCH amd64
#set -U PATH /usr/local/opt/go/bin (brew --prefix homebrew/php/php70)/bin $GOPATH/bin /tools/ssh-auto-login/auto_gen $PATH
set -gx PATH $MYRUNTIME/customs/bin $PATH
set -gx PATH /tools/ssh-auto-login/auto_gen $PATH
set -gx PATH /usr/local/opt/coreutils/libexec/gnubin $PATH
set -gx PATH $HOME/bin $PATH

##别名设置
alias goweb "godoc -http=:9900 >> /dev/null &"
alias vimgo 'vim -u ~/.vimrc.go'
alias l "ls -a"
alias lll "/usr/local/bin/ls++"
alias gopl "open ~/Documents/golang/gopl-zh/_book/index.html"
alias cl "clear"

##图片脚本设置
sh {$MYRUNTIME}/customs/bin/extendslocatetochangepicurl

##autojump设置
[ -f /usr/local/share/autojump/autojump.fish ]; and . /usr/local/share/autojump/autojump.fish

eval (thefuck --alias | tr '\n' ';')

#/usr/local/bin/screenfetch

##引入iterm2 自动变更背景脚本
if test -f {$MYRUNTIME}/customs/my_shell/fish/zmy_changebg.fish
    . {$MYRUNTIME}/customs/my_shell/fish/zmy_changebg.fish
end
