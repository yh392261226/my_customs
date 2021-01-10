### export 设定
[[ -d $HOME/.nvm ]] && export NVM_DIR="$HOME/.nvm"

### source 引入
#####nvm
if [ -s "$HOME/.nvm/nvm.sh"  ] ; then
    source ~/.nvm/nvm.sh # Loads NVM into a shell session.
fi
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"  # This loads nvm
[[ -f $HOME/.rvm/scripts/rvm ]] && source $HOME/.rvm/scripts/rvm

[[ -s $HOME/.autojump/etc/profile.d/autojump.sh  ]] && source $HOME/.autojump/etc/profile.d/autojump.sh

default_user=$(/usr/bin/whoami)

#/usr/local/bin/screenfetch

if [ "bash" = "$nowshell" ]; then
#    source $(brew --prefix grc)/etc/grc.bashrc
    #source /usr/local/etc/grc.bashrc
    #source $(brew --prefix)/etc/bash_completion
    #source $HOME/git-completion.bash
    [[ -f $HOME/.fzf.bash ]] && source $HOME/.fzf.bash
elif [ "zsh" = "$nowshell" ]; then
    source $(brew --prefix)/share/antigen/antigen.zsh
	# unset _fzf_completion_loaded
    [[ -f $HOME/.fzf.zsh ]] && source $HOME/.fzf.zsh
fi

#eval $(thefuck --alias)

/bin/sh $MYRUNTIME/customs/bin/extendslocatetochangepicurl
if [ "bash" != "$nowshell" ]; then
	source $MYRUNTIME/customs/others/iterm2_rainbow_tabs.sh
fi

[[ -f $MYRUNTIME/customs/bin/start ]] && $MYRUNTIME/customs/bin/start

export PATH="/usr/local/opt/sphinx-doc/bin:$PATH"
export LDFLAGS="-L/usr/local/opt/openssl/lib"
export CPPFLAGS="-I/usr/local/opt/openssl/include"

#fasd
eval "$(fasd --init auto)"


#vim&nvim  remote
if [ -f $HOME/.SpaceVim ] || [ -d $HOME/.SpaceVim ]; then 
	export PATH=$PATH:$HOME/.SpaceVim/bin
fi
