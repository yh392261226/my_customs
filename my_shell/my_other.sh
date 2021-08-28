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

### vim&nvim  remote
if [ -f $HOME/.SpaceVim ] || [ -d $HOME/.SpaceVim ]; then 
	export PATH=$HOME/.SpaceVim/bin:$PATH
fi

[[ -d ~/.yarn/bin ]] && export PATH="~/.yarn/bin:$PATH"
[[ -d ~/.local/bin ]] && export PATH="~/.local/bin:$PATH"

### iterm2 shell integration
[[ -e $HOME/.iterm2_shell_integration.${nowshell} ]] && source $HOME/.iterm2_shell_integration.${nowshell}

#{{{ OH-MY-ZSH & Zinit plugins
if [ "zsh" = "$nowshell" ]; then
    if [ ! -d $HOME/.zinit/plugins ]; then
        mkdir -p $HOME/.zinit/plugins
    fi

    if [ ! -d ${MYRUNTIME}/customs/others/fuzzy-fs/ ] && [ ! -d $HOME/.zinit/plugins/yh392261226---fuzzy-fs ]; then
        git clone --depth=1 https://github.com/yh392261226/fuzzy-fs.git $HOME/.zinit/plugins/yh392261226---fuzzy-fs
        ln -sf $HOME/.zinit/plugins/yh392261226---fuzzy-fs ${MYRUNTIME}/customs/others/fuzzy-fs
        is_notify=1
    else
        [[ -f ${MYRUNTIME}/customs/others/fuzzy-fs/fuzzy-fs ]] && source ${MYRUNTIME}/customs/others/fuzzy-fs/fuzzy-fs
    fi

    if [ ! -d ${MYRUNTIME}/customs/others/zsh-fzf-widgets/ ] && [ ! -d $HOME/.zinit/plugins/amaya382---zsh-fzf-widgets ]; then
        git clone --depth=1 https://github.com/amaya382/zsh-fzf-widgets.git $HOME/.zinit/plugins/amaya382---zsh-fzf-widgets
        ln -sf $HOME/.zinit/plugins/amaya382---zsh-fzf-widgets ${MYRUNTIME}/customs/others/zsh-fzf-widgets
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

    if [ ! -d ${MYRUNTIME}/customs/others/zfm ] && [ ! -d $HOME/.zinit/plugins/pabloariasal---zfm ]; then
        git clone --depth=1 https://github.com/pabloariasal/zfm $HOME/.zinit/plugins/pabloariasal---zfm
        ln -sf $HOME/.zinit/plugins/pabloariasal---zfm ${MYRUNTIME}/customs/others/zfm
        is_notify=1
    else
        [[ -f ${MYRUNTIME}/customs/others/zfm/zfm.zsh ]] && source ${MYRUNTIME}/customs/others/zfm/zfm.zsh
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-fzf-widgets ] && [ ! -d $HOME/.zinit/plugins/amaya382---zsh-fzf-widgets ]; then
        git clone https://github.com/amaya382/zsh-fzf-widgets.git $HOME/.zinit/plugins/amaya382---zsh-fzf-widgets
        ln -sf $HOME/.zinit/plugins/amaya382---zsh-fzf-widgets ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-fzf-widgets
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-zsh-completions ] && [ ! -d $HOME/.zinit/plugins/chitoku-k---fzf-zsh-completions ]; then
        git clone https://github.com/chitoku-k/fzf-zsh-completions.git $HOME/.zinit/plugins/chitoku-k---fzf-zsh-completions
        ln -sf $HOME/.zinit/plugins/chitoku-k---fzf-zsh-completions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-zsh-completions
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/alias-tips ] && [ ! -d $HOME/.zinit/plugins/djui---alias-tips ]; then
        git clone https://github.com/djui/alias-tips $HOME/.zinit/plugins/djui---alias-tips
        ln -sf $HOME/.zinit/plugins/djui---alias-tips ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/alias-tips
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/yeoman ] && [ ! -d $HOME/.zinit/plugins/edouard-lopez---yeoman-zsh-plugin ]; then
        git clone https://github.com/edouard-lopez/yeoman-zsh-plugin $HOME/.zinit/plugins/edouard-lopez---yeoman-zsh-plugin
        ln -sf $HOME/.zinit/plugins/edouard-lopez---yeoman-zsh-plugin ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/yeoman
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-apple-touchbar ] && [ ! -d $HOME/.zinit/plugins/floor114---zsh-apple-touchbar ]; then
        git clone https://github.com/floor114/zsh-apple-touchbar $HOME/.zinit/plugins/floor114---zsh-apple-touchbar
        ln -sf $HOME/.zinit/plugins/floor114---zsh-apple-touchbar ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-apple-touchbar
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/mysql-colorize ] && [ ! -d $HOME/.zinit/plugins/horosgrisa---mysql-colorize ]; then
        git clone https://github.com/horosgrisa/mysql-colorize $HOME/.zinit/plugins/horosgrisa---mysql-colorize
        ln -sf $HOME/.zinit/plugins/horosgrisa---mysql-colorize ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/mysql-colorize
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-iterm-touchbar ] && [ ! -d $HOME/.zinit/plugins/iam4x---zsh-iterm-touchbar ]; then
        git clone https://github.com/iam4x/zsh-iterm-touchbar $HOME/.zinit/plugins/iam4x---zsh-iterm-touchbar
        ln -sf $HOME/.zinit/plugins/iam4x---zsh-iterm-touchbar ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-iterm-touchbar
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/hhighlighter ] && [ ! -d $HOME/.zinit/plugins/paoloantinori---hhighlighter ]; then
        git clone https://github.com/paoloantinori/hhighlighter $HOME/.zinit/plugins/paoloantinori---hhighlighter
        ln -sf $HOME/.zinit/plugins/paoloantinori---hhighlighter ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/hhighlighter
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/git-open ] && [ ! -d $HOME/.zinit/plugins/paulirish---git-open ]; then
        git clone https://github.com/paulirish/git-open $HOME/.zinit/plugins/paulirish---git-open
        ln -sf $HOME/.zinit/plugins/paulirish---git-open ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/git-open
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/powerlevel10k ] && [ ! -d $HOME/.zinit/plugins/romkatv---powerlevel10k ]; then
        git clone https://github.com/romkatv/powerlevel10k $HOME/.zinit/plugins/romkatv---powerlevel10k
        ln -sf $HOME/.zinit/plugins/romkatv---powerlevel10k ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/powerlevel10k
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/codeception-zsh-plugin ] && [ ! -d $HOME/.zinit/plugins/shengyou---codeception-zsh-plugin ]; then
        git clone https://github.com/shengyou/codeception-zsh-plugin $HOME/.zinit/plugins/shengyou---codeception-zsh-plugin
        ln -sf $HOME/.zinit/plugins/shengyou---codeception-zsh-plugin ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/codeception-zsh-plugin
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/z.lua ] && [ ! -d $HOME/.zinit/plugins/skywind3000---z.lua ]; then
        git clone https://github.com/skywind3000/z.lua $HOME/.zinit/plugins/skywind3000---z.lua
        ln -sf $HOME/.zinit/plugins/skywind3000---z.lua ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/z.lua
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-tab ] && [ ! -d $HOME/.zinit/plugins/Aloxaf---fzf-tab ]; then
        git clone https://github.com/Aloxaf/fzf-tab $HOME/.zinit/plugins/Aloxaf---fzf-tab
        ln -sf $HOME/.zinit/plugins/Aloxaf---fzf-tab ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fzf-tab
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-interactive-cd ] && [ ! -d $HOME/.zinit/plugins/changyuheng---zsh-interactive-cd ]; then
        git clone https://github.com/changyuheng/zsh-interactive-cd.git $HOME/.zinit/plugins/changyuheng---zsh-interactive-cd
        ln -sf $HOME/.zinit/plugins/changyuheng---zsh-interactive-cd ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-interactive-cd
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/formarks ] && [ ! -d $HOME/.zinit/plugins/wfxr---formarks ]; then
        git clone https://github.com/wfxr/formarks.git $HOME/.zinit/plugins/wfxr---formarks
        ln -sf $HOME/.zinit/plugins/wfxr---formarks ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/formarks
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fast-syntax-highlighting ] && [ ! -d $HOME/.zinit/plugins/zdharma---fast-syntax-highlighting ]; then
        git clone https://github.com/zdharma/fast-syntax-highlighting $HOME/.zinit/plugins/zdharma---fast-syntax-highlighting
        ln -sf $HOME/.zinit/plugins/zdharma---fast-syntax-highlighting ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fast-syntax-highlighting
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zbrowse ] && [ ! -d $HOME/.zinit/plugins/zdharma---zbrowse ]; then
        git clone https://github.com/zdharma/zbrowse $HOME/.zinit/plugins/zdharma---zbrowse
        ln -sf $HOME/.zinit/plugins/zdharma---zbrowse ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zbrowse
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zui ] && [ ! -d $HOME/.zinit/plugins/zdharma---zui ]; then
        git clone https://github.com/zdharma/zui $HOME/.zinit/plugins/zdharma---zui
        ln -sf $HOME/.zinit/plugins/zdharma---zui ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zui
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions ] && [ ! -d $HOME/.zinit/plugins/zsh-users---zsh-autosuggestions ]; then
        git clone https://github.com/zsh-users/zsh-autosuggestions $HOME/.zinit/plugins/zsh-users---zsh-autosuggestions
        ln -sf $HOME/.zinit/plugins/zsh-users---zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-completions ] && [ ! -d $HOME/.zinit/plugins/zsh-users---zsh-completions ]; then
        git clone https://github.com/zsh-users/zsh-completions $HOME/.zinit/plugins/zsh-users---zsh-completions
        ln -sf $HOME/.zinit/plugins/zsh-users---zsh-completions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-completions
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-history-substring-search ] && [ ! -d $HOME/.zinit/plugins/zsh-users---zsh-history-substring-search ]; then
        git clone https://github.com/zsh-users/zsh-history-substring-search $HOME/.zinit/plugins/zsh-users---zsh-history-substring-search
        ln -sf $HOME/.zinit/plugins/zsh-users---zsh-history-substring-search ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-history-substring-search
        is_notify=1
    fi

    if [ ! -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting ] && [ ! -d $HOME/.zinit/plugins/zsh-users---zsh-syntax-highlighting ]; then
        git clone https://github.com/zsh-users/zsh-syntax-highlighting $HOME/.zinit/plugins/zsh-users---zsh-syntax-highlighting
        ln -sf $HOME/.zinit/plugins/zsh-users---zsh-syntax-highlighting ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
        is_notify=1
    fi
fi
#}}}
if [ ! -d $MYRUNTIME/customs/others/enhancd/ ]; then
    git clone https://github.com/yh392261226/enhancd $MYRUNTIME/customs/others/enhancd
    is_notify=1
fi
if [ -d $MYRUNTIME/customs/others/enhancd/ ]; then
    export ENHANCD_COMMAND=ecd
    source $MYRUNTIME/customs/others/enhancd/my_init.sh
    [[ -f /usr/local/bin/peco ]] && export ENHANCD_FILTER="/usr/local/bin/peco:fzf:non-existing-filter"
    [[ -f /opt/homebrew/bin/peco ]] && export ENHANCD_FILTER="/opt/homebrew/bin/peco:fzf:non-existing-filter"
    export ENHANCD_HOOK_AFTER_CD="lsd -l"
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

### SSH config && tmp directory
[[ ! -f $HOME/.ssh/config ]] && ln -sf $MYRUNTIME/customs/customs_modify_records/ssh_config $HOME/.ssh/config
[[ ! -d $HOME/.ssh/tmp ]] && mkdir -p $HOME/.ssh/tmp

### fz
if [ ! -d $MYRUNTIME/customs/others/fz ]; then
    git clone https://github.com/changyuheng/fz.git $MYRUNTIME/customs/others/fz
fi

if [ -f $MYRUNTIME/customs/others/fz/fz.sh ]; then
	source $MYRUNTIME/customs/others/fz/fz.sh
fi

### zinit
if [ ! -d $MYRUNTIME/customs/others/zinit ]; then
    git clone https://github.com/zdharma/zinit.git $MYRUNTIME/customs/others/zinit
fi

### tag
if [ "zsh" = "$nowshell" ]; then
    if (( $+commands[tag] )); then
        export TAG_SEARCH_PROG=ag  # replace with rg for ripgrep
        tag() { command tag "$@"; source ${TAG_ALIAS_FILE:-/tmp/tag_aliases} 2>/dev/null; }
        alias ag="tag"  # replace with rg for ripgrep
    fi
fi

if [ "bash" = "$nowshell" ]; then
    if hash ag 2>/dev/null; then
        export TAG_SEARCH_PROG=ag  # replace with rg for ripgrep
        tag() { command tag "$@"; source ${TAG_ALIAS_FILE:-/tmp/tag_aliases} 2>/dev/null; }
        alias ag=tag  # replace with rg for ripgrep
    fi
fi

###zoxide
if [ "" != "$(brew --prefix zoxide)" ]; then
    if [ "zsh" = "$nowshell" ]; then
        eval "$(zoxide init zsh)"
    fi
    if [ "bash" = "$nowshell" ]; then
        eval "$(zoxide init bash)"
    fi
fi

### custom commands
## fasd
eval "$(fasd --init auto)"
## the fuck command
eval $(thefuck --alias)
## the aliases command
eval "$(aliases init --global)"
## the atuin import
if [ "zsh" = "$nowshell" ]; then
    eval "$(atuin init zsh)"
elif [ "bash" = "$nowshell" ]; then
    eval "$(atuin init bash)"
fi


default_user=$(/usr/bin/whoami)
/bin/sh $MYRUNTIME/customs/bin/extendslocatetochangepicurl
