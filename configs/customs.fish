set -gx MYRUNTIME (cat $HOME/.myruntime)
set -gx GOPATH $HOME/go-develop
set -gx GOOS darwin
set -gx GOARCH arm64
if test -d /usr/local/opt/go/bin
  set -gx PATH /usr/local/opt/go/bin $GOPATH/bin $PATH
end
if test -d /opt/homebrew/opt/go/bin
  set -gx PATH /opt/homebrew/opt/go/bin $GOPATH/bin $PATH
end
set -gx PATH /opt/homebrew/opt/go/libexec/bin $PATH

alias goweb "godoc -http=:9900 >> /dev/null &"
alias vimgo 'vim -u $HOME/.vimrc.go'
alias l "ls -a"
if test -e /usr/local/bin/ls++
  alias lll "/usr/local/bin/ls++"
end

if test -d $HOME/Documents/golang/gopl-zh/_book/
  alias gopl "open $HOME/Documents/golang/gopl-zh/_book/index.html"
end

$MYRUNTIME/customs/bin/theme ($MYRUNTIME/customs/bin/theme -l|tail -n1)
