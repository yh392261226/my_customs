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
    [[ -f /opt/homebrew/share/antigen/antigen.zsh ]] && source /opt/homebrew/share/antigen/antigen.zsh
    [[ -f /usr/local/share/antigen/antigen.zsh ]] && source /usr/local/share/antigen/antigen.zsh
	# unset _fzf_completion_loaded
    [[ -f $HOME/.fzf.zsh ]] && source $HOME/.fzf.zsh
fi

eval $(thefuck --alias)

/bin/sh $MYRUNTIME/customs/bin/extendslocatetochangepicurl
if [ "bash" != "$nowshell" ]; then
	source $MYRUNTIME/customs/others/iterm2_rainbow_tabs.sh
fi

[[ -f $MYRUNTIME/customs/bin/start ]] && $MYRUNTIME/customs/bin/start

[[ -d /usr/local/opt/sphinx-doc/bin ]] && export PATH="/usr/local/opt/sphinx-doc/bin:$PATH"
[[ -d /opt/homebrew/opt/sphinx-doc/bin ]] && export PATH="/opt/homebrew/opt/sphinx-doc/bin:$PATH"
[[ -d /usr/local/opt/openssl/lib ]] && export LDFLAGS="-L/usr/local/opt/openssl/lib"
[[ -d /opt/homebrew/opt/openssl/lib ]] && export LDFLAGS="-L/opt/homebrew/opt/openssl/lib"
[[ -d /usr/local/opt/openssl/include ]] && export CPPFLAGS="-I/usr/local/opt/openssl/include"
[[ -d /opt/homebrew/opt/openssl/include ]] && export CPPFLAGS="-I/opt/homebrew/opt/openssl/include"

#fasd
eval "$(fasd --init auto)"


#vim&nvim  remote
if [ -f $HOME/.SpaceVim ] || [ -d $HOME/.SpaceVim ]; then 
	export PATH=$PATH:$HOME/.SpaceVim/bin
fi

if [ -d $MYRUNTIME/customs/enhancd/ ]; then
    export ENHANCD_COMMAND=ecd
    source $MYRUNTIME/customs/enhancd/my_init.sh
    [[ -f /usr/local/bin/peco ]] && export ENHANCD_FILTER="/usr/local/bin/peco:fzf:non-existing-filter"
    [[ -f /opt/homebrew/bin/peco ]] && export ENHANCD_FILTER="/opt/homebrew/bin/peco:fzf:non-existing-filter"
    export ENHANCD_HOOK_AFTER_CD="lsd -l"
fi

#iterm2 shell integration
[[ -e $HOME/.iterm2_shell_integration.${nowshell} ]] && source $HOME/.iterm2_shell_integration.${nowshell}
