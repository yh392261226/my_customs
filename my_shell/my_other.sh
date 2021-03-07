#!/bin/bash
# File              : my_other.sh
# Date              : 27.02.2021
# Last Modified Date: 27.02.2021
is_notify=0
### export 设定
[[ -d $HOME/.nvm ]] && export NVM_DIR="$HOME/.nvm"

### source 引入
#####nvm
[[ -s "$HOME/.nvm/nvm.sh"  ]] && source ~/.nvm/nvm.sh # Loads NVM into a shell session.
[[ -s "$NVM_DIR/nvm.sh" ]] && source "$NVM_DIR/nvm.sh"  # This loads nvm
[[ -f $HOME/.rvm/scripts/rvm ]] && source $HOME/.rvm/scripts/rvm
[[ -s $HOME/.autojump/etc/profile.d/autojump.sh  ]] && source $HOME/.autojump/etc/profile.d/autojump.sh

if [ "bash" = "$nowshell" ]; then
    [[ -f $HOME/.fzf.bash ]] && source $HOME/.fzf.bash
elif [ "zsh" = "$nowshell" ]; then
    [[ -f /opt/homebrew/share/antigen/antigen.zsh ]] && source /opt/homebrew/share/antigen/antigen.zsh
    [[ -f /usr/local/share/antigen/antigen.zsh ]] && source /usr/local/share/antigen/antigen.zsh
    [[ -f $HOME/.fzf.zsh ]] && source $HOME/.fzf.zsh
fi

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

#vim&nvim  remote
if [ -f $HOME/.SpaceVim ] || [ -d $HOME/.SpaceVim ]; then 
	export PATH=$HOME/.SpaceVim/bin:$PATH
fi

[[ -d ~/.yarn/bin ]] && export PATH="~/.yarn/bin:$PATH"
[[ -d ~/.local/bin ]] && export PATH="~/.local/bin:$PATH"

#iterm2 shell integration
[[ -e $HOME/.iterm2_shell_integration.${nowshell} ]] && source $HOME/.iterm2_shell_integration.${nowshell}

if [ "zsh" = "$nowshell" ]; then
    if [ ! -d ${MYRUNTIME}/customs/others/fuzzy-fs/ ]; then
        git clone --depth=1 https://github.com/SleepyBag/fuzzy-fs.git ${MYRUNTIME}/customs/others/fuzzy-fs
        cp $MYRUNTIME/customs/customs_modify/fuzzy-fs ${MYRUNTIME}/customs/others/fuzzy-fs/fuzzy-fs
        cp $MYRUNTIME/customs/customs_modify/_fuzzy-fs-list-recent-dir ${MYRUNTIME}/customs/others/fuzzy-fs/module/recent-dir/_fuzzy-fs-list-recent-dir
        is_notify=1
    else
        [[ -f ${MYRUNTIME}/customs/others/fuzzy-fs/fuzzy-fs ]] && source ${MYRUNTIME}/customs/others/fuzzy-fs/fuzzy-fs
    fi

    if [ ! -d ${MYRUNTIME}/customs/others/zsh-fzf-widgets/ ]; then
        git clone --depth=1 https://github.com/amaya382/zsh-fzf-widgets.git ${MYRUNTIME}/customs/others/zsh-fzf-widgets
        is_notify=1
    else
        [[ -f ${MYRUNTIME}/customs/others/zsh-fzf-widgets/zsh-fzf-widgets.zsh ]] && source ${MYRUNTIME}/customs/others/zsh-fzf-widgets/zsh-fzf-widgets.zsh
    fi

    if [ ! -d ${MYRUNTIME}/customs/others/git-fuzzy ]; then
        git clone --depth=1 https://github.com/bigH/git-fuzzy.git ${MYRUNTIME}/customs/others/git-fuzzy
        is_notify=1
    else
        [[ -d ${MYRUNTIME}/customs/others/git-fuzzy/bin ]] && export PATH="${MYRUNTIME}/customs/others/git-fuzzy/bin:$PATH"
    fi

    if [ ! -d ${MYRUNTIME}/customs/others/zfm ]; then
        git clone --depth=1 https://github.com/pabloariasal/zfm ${MYRUNTIME}/customs/others/zfm
        is_notify=1
    else
        [[ -f ${MYRUNTIME}/customs/others/zfm/zfm.zsh ]] && source ${MYRUNTIME}/customs/others/zfm/zfm.zsh
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-fzf-widgets ]; then
        git clone https://github.com/amaya382/zsh-fzf-widgets.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-fzf-widgets
    fi
    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-zsh-completions ]; then
        git clone https://github.com/chitoku-k/fzf-zsh-completions.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-zsh-completions
    fi
    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-tab ]; then
        git clone https://github.com/Aloxaf/fzf-tab ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-tab
    fi
fi

if [ ! -d $MYRUNTIME/customs/others/enhancd/ ]; then
    git clone https://github.com/b4b4r07/enhancd $MYRUNTIME/customs/others/enhancd
    cp $MYRUNTIME/customs/customs_modify/enhancd.sh $MYRUNTIME/customs/others/enhancd/my_init.sh
    is_notify=1
else
    if [ -d $MYRUNTIME/customs/others/enhancd/ ]; then
        export ENHANCD_COMMAND=ecd
        source $MYRUNTIME/customs/others/enhancd/my_init.sh
        [[ -f /usr/local/bin/peco ]] && export ENHANCD_FILTER="/usr/local/bin/peco:fzf:non-existing-filter"
        [[ -f /opt/homebrew/bin/peco ]] && export ENHANCD_FILTER="/opt/homebrew/bin/peco:fzf:non-existing-filter"
        export ENHANCD_HOOK_AFTER_CD="lsd -l"
    fi
fi

if [ "$is_notify" -gt "0" ]; then
    echo "Please Restart a new terminal window to effect the changing !!!"
fi

#custom commands
#fasd
eval "$(fasd --init auto)"
#the fuck command
eval $(thefuck --alias)

default_user=$(/usr/bin/whoami)
/bin/sh $MYRUNTIME/customs/bin/extendslocatetochangepicurl