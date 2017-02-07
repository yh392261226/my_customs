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

if [ "bash" = "$nowshell" ]; then
#    source $(brew --prefix grc)/etc/grc.bashrc
    source /usr/local/etc/grc.bashrc
    source $(brew --prefix)/etc/bash_completion
    source ~/git-completion.bash
    [ -f ~/.fzf.bash ] && source ~/.fzf.bash
elif [ "zsh" = "$nowshell" ]; then
    source $(brew --prefix)/share/antigen/antigen.zsh
	# unset _fzf_completion_loaded
    [ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
fi

eval $(thefuck --alias)

/bin/sh $MYRUNTIME/tools/extendslocatetochangepicurl.sh
