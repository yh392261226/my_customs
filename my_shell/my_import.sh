### 配置文件引入
source $MYRUNTIME/customs/my_shell/go.sh
source $MYRUNTIME/customs/my_shell/php.sh
source $MYRUNTIME/customs/my_shell/ser.sh
# Z integration
source $HOME/z.sh
unalias z 2> /dev/null

curshell() {
    curshell=$(env | grep RBENV_SHELL)
    if [ "" = "$curshell" ]; then
        curshell=$(env | grep PYENV_SHELL)
        if [ "$curshell" = "PYENV_SHELL=bash" ]; then
            echo "bash"
        else
            echo "Unknow"
        fi
    elif [ "$curshell" = "RBENV_SHELL=zsh" ]; then
        echo "zsh"
    else
            echo "Unknow"
    fi
}

export nowshell=$(curshell)

if [ "bash" = "$nowshell" ]; then
    source $(brew --prefix grc)/etc/grc.bashrc
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



