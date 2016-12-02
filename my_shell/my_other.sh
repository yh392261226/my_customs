### export 设定
export NVM_DIR="/Users/json/.nvm"
#####GO
export GOROOT=$(brew --prefix go)

### source 引入
#####nvm
if [ -s "$HOME/.nvm/nvm.sh"  ] ; then
    source ~/.nvm/nvm.sh # Loads NVM into a shell session.
fi
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"  # This loads nvm

[[ -s ~/.autojump/etc/profile.d/autojump.sh  ]] && source ~/.autojump/etc/profile.d/autojump.sh

default_user=$(/usr/bin/whoami)

/usr/local/bin/screenfetch
