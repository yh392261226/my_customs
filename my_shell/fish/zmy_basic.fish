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
set -gx PATH $HOME/.cargo/bin $PATH
set -gx PATH $HOME/.local/bin $PATH

##别名设置
alias goweb "godoc -http=:9900 >> /dev/null &"
alias vimgo 'vim -u ~/.vimrc.go'
alias l "ls -a"
alias lll "/usr/local/bin/ls++"
alias gopl "open ~/Documents/golang/gopl-zh/_book/index.html"
alias cl "clear"

##版本控制 git 别名设置
alias gs "git status"
alias gpl "git pull"
alias gp 'git push'
alias gps "git push"
alias gsh "git show"
alias gith "git stash"
alias gsta 'git stash save'
alias gstaa 'git stash apply'
alias gstc 'git stash clear'
alias gstd 'git stash drop'
alias gstl 'git stash list'
alias gstp 'git stash pop'
alias gsts 'git stash show --text'
alias gsu='git submodule update'
##版本控制 hg 别名设置
alias hgs 'hg status'
alias hgu 'hg update'
alias hgpl 'hg pull'
alias hgpu 'hg push'
alias hgc 'hg clone'

##cd 别名设置
alias cd.. 'cd ../'                         # Go back 1 directory level (for fast typers)
alias cd. 'cd ..'
alias .. 'cd ../'                           # Go back 1 directory level
alias ... 'cd ../../'                       # Go back 2 directory levels
alias .3 'cd ../../../'                     # Go back 3 directory levels
alias .4 'cd ../../../../'                  # Go back 4 directory levels
alias .5 'cd ../../../../../'               # Go back 5 directory levels
alias .6 'cd ../../../../../../'            # Go back 6 directory levels
alias .... 'cd ../../..'
alias ..... 'cd ../../../..'
alias ...... 'cd ../../../../..'

##解压 别名设置
alias gz 'tar -zxvf'
alias tgz 'tar -zxvf'
alias bz2 'tar -xjvf'

##函数
function goto
  if test -d $argv
    cd $argv
  else
    cd (dirname $argv)
  end
end

##图片脚本设置
sh {$MYRUNTIME}/customs/bin/extendslocatetochangepicurl

##引入iterm2 自动变更背景脚本
#source {$MYRUNTIME}/customs/my_shell/fish/zmy_changebg.fish
