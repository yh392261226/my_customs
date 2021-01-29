#####goroot
#export GOROOT=$HOME/go1.4
#export PATH=$PATH:$HOME/go1.4/bin
[[ -s "$HOME/.gvm/scripts/gvm" ]] && source "$HOME/.gvm/scripts/gvm"
export GOROOT=$(brew --prefix go)/libexec
export PATH=$PATH:$(brew --prefix go)/libexec/bin
export GOPATH=$HOME/go-develop
export PATH=$PATH:$GOPATH/bin
export GOOS=darwin
export GOARCH=amd64
export GO111MODULE=on
#export GOBOOK=$HOME/go-develop/gobook
#. $GOBOOK/env.sh
alias goweb="godoc -http=:9900 >> /dev/null &"
#alias gopl="open ~/Documents/golang/gopl-zh/_book/index.html"
