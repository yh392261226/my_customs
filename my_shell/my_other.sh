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
        git clone --depth=1 https://github.com/yh392261226/fuzzy-fs.git ${MYRUNTIME}/customs/others/fuzzy-fs
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
        is_notify=1
    fi
    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-zsh-completions ]; then
        git clone https://github.com/chitoku-k/fzf-zsh-completions.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-zsh-completions
        is_notify=1
    fi
    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-tab ]; then
        git clone https://github.com/Aloxaf/fzf-tab ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-tab
        is_notify=1
    fi
    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-interactive-cd ]; then
        git clone https://github.com/changyuheng/zsh-interactive-cd.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-interactive-cd
        is_notify=1
    fi
    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/formarks ]; then
        git clone https://github.com/wfxr/formarks.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/formarks
        is_notify=1
    fi
fi

if [ ! -d $MYRUNTIME/customs/others/enhancd/ ]; then
    git clone https://github.com/yh392261226/enhancd $MYRUNTIME/customs/others/enhancd
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

if [ ! -d $MYRUNTIME/customs/others/SSHAutoLogin  ]; then
    git clone https://github.com/yh392261226/SSHAutoLogin.git $MYRUNTIME/customs/others/SSHAutoLogin
    $MYRUNTIME/customs/others/SSHAutoLogin/install.sh
fi

if [ ! -d $MYRUNTIME/customs/others/up ]; then
    git clone https://github.com/shannonmoeller/up $MYRUNTIME/customs/others/up
    ln -sf $MYRUNTIME/customs/others/up/up.fish $HOME/.config/fish/conf.d/up.fish
fi
source $MYRUNTIME/customs/others/up/up.sh

#[[ -f /opt/homebrew/opt/autoenv/activate.sh ]] && source /opt/homebrew/opt/autoenv/activate.sh
#[[ -f /usr/local/opt/autoenv/activate.sh ]] && source /usr/local/opt/autoenv/activate.sh
[[ -f /opt/homebrew/bin/pokemon ]] && alias ding="/opt/homebrew/bin/pokemon"
[[ -f /usr/local/bin/pokemon ]] && alias ding="/usr/local/bin/pokemon"

if [ "$is_notify" -gt "0" ]; then
    echo "Please Restart a new terminal window to effect the changing !!!"
fi

#M1 sqlite3
if [ -d /opt/homebrew/opt/sqlite/bin ]; then
	export PATH="/opt/homebrew/opt/sqlite/bin:$PATH"
	export LDFLAGS="-L/opt/homebrew/opt/sqlite/lib"
	export CPPFLAGS="-I/opt/homebrew/opt/sqlite/include"
	export PKG_CONFIG_PATH="/opt/homebrew/opt/sqlite/lib/pkgconfig"
fi

### Bashhub.com Installation
if [ ! -d $HOME/.bashhub/ ]; then
	curl -OL https://bashhub.com/setup && zsh setup
fi

if [ "zsh" = "$nowshell" ]; then
	if [ -f $HOME/.bashhub/bashhub.zsh ]; then
    	source $HOME/.bashhub/bashhub.zsh
	fi
fi
if [ "bash" = "$nowshell" ]; then
	if [ -f $HOME/.bashhub/bashhub.bash ]; then
		source $HOME/.bashhub/bashhub.bash
	fi
fi

if [ "$(command -v atuin)"  =  "" ]; then
    brew install atuin
fi

#SSH config && tmp directory
[[ ! -f $HOME/.ssh/config ]] && ln -sf $MYRUNTIME/customs/customs_modify_records/ssh_config $HOME/.ssh/config
[[ ! -d $HOME/.ssh/tmp ]] && mkdir -p $HOME/.ssh/tmp

#custom commands
#fasd
eval "$(fasd --init auto)"
#the fuck command
eval $(thefuck --alias)
#the aliases command
eval "$(aliases init --global)"
#the atuin import
if [ "zsh" = "$nowshell" ]; then
    eval "$(atuin init zsh)"
elif [ "bash" = "$nowshell" ]; then
    eval "$(atuin init bash)"
fi


default_user=$(/usr/bin/whoami)
/bin/sh $MYRUNTIME/customs/bin/extendslocatetochangepicurl
