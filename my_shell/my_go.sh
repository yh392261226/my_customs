#####goroot
#export GOROOT=$HOME/go1.4
#export PATH=$PATH:$HOME/go1.4/bin
[[ -s "$HOME/.gvm/scripts/gvm" ]] && source "$HOME/.gvm/scripts/gvm"
export GOROOT=$(brew --prefix go)/libexec
export GOPATH=$HOME/go-develop
#export GOBIN=$GOPATH/bin
export PATH=$(brew --prefix go)/libexec/bin:$PATH
export PATH=$GOPATH/bin:$PATH
export GOOS=darwin
export GOARCH=arm64
export GO111MODULE=on
#export GOBOOK=$HOME/go-develop/gobook
#. $GOBOOK/env.sh
alias goweb="godoc -http=:9900 >> /dev/null &"                                                                      # Desc: alias: goweb:godoc的web版别名
#alias gopl="open ~/Documents/golang/gopl-zh/_book/index.html"
