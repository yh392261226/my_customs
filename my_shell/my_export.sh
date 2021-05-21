### 环境变量设定
export PLATFORM=$(uname -s)
export BASE=$HOME
[[ -d /usr/local/opt/macvim ]] && export PATH="/usr/local/opt/macvim/bin:/usr/local/bin:$PATH"
[[ -d /opt/homebrew/opt/macvim ]] && export PATH="/opt/homebrew/opt/macvim/bin:/usr/local/bin:$PATH"
[[ -d /usr/local/var/rbenv ]] && export RBENV_ROOT=/usr/local/var/rbenv && eval "$(rbenv init -)"
[[ -d /usr/local/opt/python ]] && export PATH="/usr/local/opt/python/bin:$PATH"
[[ -d /opt/homebrew/opt/python ]] && export PATH="/opt/homebrew/opt/python/bin:$PATH"
[[ -d /usr/local/opt/python@2/libexec/bin ]] && export PATH="/usr/local/opt/python@2/libexec/bin:$PATH"
[[ -d $HOME/.cargo/bin ]] && export PATH="$HOME/.cargo/bin:/opt/local/bin:$PATH"
[[ -d /opt/local/bin ]] && export PATH="/opt/local/bin:$PATH"
[[ -d $HOME/.local/bin ]] && export PATH="$HOME/.local/bin:$PATH"
[[ -d /usr/local/opt/pyenv ]] && export PYENV_ROOT="/usr/local/var/pyenv" && PATH="$PYENV_ROOT/bin:$PATH" && eval "$(pyenv init -)"
if which pyenv-virtualenv-init > /dev/null; then eval "$(pyenv virtualenv-init -)"; fi

#####设置PATH变量
if [ "$MYSYSNAME" = "Mac" ]; then
    [[ -d /usr/bin ]] && export PATH="/usr/bin:$PATH"
    [[ -d /bin ]] && export PATH="/bin:$PATH"
    [[ -d /usr/sbin ]] && export PATH="/usr/sbin:$PATH"
    [[ -d /sbin ]] && export PATH="/sbin:$PATH"
    [[ -d /usr/local/bin ]] && export PATH="/usr/local/bin:$PATH"
    [[ -d /usr/local/sbin ]] && export PATH="/usr/local/sbin:$PATH"
    [[ -d /usr/local/var/rbenv/shims ]] && export PATH="/usr/local/var/rbenv/shims:$PATH"
    [[ -d $HOME/go/bin ]] && export PATH="$HOME/go/bin:$PATH"
    [[ -d $HOME/.cabal/bin ]] && export PATH="$HOME/.cabal/bin:$PATH"
    [[ -d $HOME/bin ]] && export PATH="$HOME/bin:$PATH"
    [[ -d /usr/local/opt/go/bin ]] && export PATH="/usr/local/opt/go/bin:$PATH"
    [[ -d /usr/local/heroku/bin ]] && export PATH="/usr/local/heroku/bin:$PATH"
    [[ -d $MYRUNTIME/customs/bin ]] && export PATH="$MYRUNTIME/customs/bin:$PATH"
    [[ -d /usr/local/opt/llvm/bin ]] && export PATH="/usr/local/opt/llvm/bin:$PATH"
    [[ -d /usr/local/opt/coreutils/libexec/gnubin ]] && export PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"
    [[ -d $HOME/.Pokemon-Terminal ]] && export PATH="$HOME/.Pokemon-Terminal:$PATH"
    [[ -d /usr/local/anaconda3/bin ]] && export PATH="/usr/local/anaconda3/bin/:$PATH"
    [[ -d /opt/homebrew/bin ]] && export PATH="/opt/homebrew/bin:$PATH"
    [[ -d /opt/homebrew/sbin ]] && export PATH="/opt/homebrew/sbin:$PATH"
    [[ -d /opt/homebrew/opt/grep/bin ]] && export PATH="/opt/homebrew/opt/grep/bin:$PATH"
    [[ -d /opt/homebrew/opt/icu4c/bin ]] && export PATH="/opt/homebrew/opt/icu4c/bin:$PATH"
else
    export PATH=/usr/local/rvm/bin:$HOME/.cabal/bin:/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin:/usr/local/sbin:$PATH
fi

######设置editor
if [ "$MYSYSNAME" = "Mac" ]; then
    if [ -f /usr/local/bin/code ]; then
        export EDITOR="/usr/local/bin/code"
    else
        export EDITOR="vim"
    fi
elif [ "$MYSYSNAME" = "Ubuntu" ] || [ "$MYSYSNAME" = "Centos" ]; then
    export EDITOR="gedit"
fi

export GIT_MERGE_AUTOEDIT=no  #while git pull does not open merge editor
if [ -d $HOME/.basher ]; then
    export PATH="$HOME/.basher/bin:$PATH"
    eval "$(basher init -)"
fi

#wine 不输出debug信息
export WINEDEBUG=-all
export MYCUSTOMS=$MYRUNTIME/customs
export MYTOOLS=$MYRUNTIME/tools

FZF_DEFAULT_COMMAND="fd --exclude={.git,.idea,.vscode,.sass-cache,node_modules,build}"

export FZF_DEFAULT_OPTS="--height 60% --multi --cycle --inline-info --ansi --border --layout=reverse --preview '(bat --color=always {} || exa {}) 2> /dev/null | head -500'  --preview-window right:70%:noborder --color 'fg:252,bg:233,hl:67,fg+:252,bg+:235,hl+:81,info:144,prompt:161,spinner:135,pointer:135,marker:118,border:254'"
export FZF_COMPLETION_OPTS="-1 --cycle --inline-info --ansi --height 60% --border --layout=reverse --preview '$PREVIEW {}' --preview-window 'right:70%:wrap'  $FZF_PREVIEW_KEY_BIND"

export FZF_TAB_OPTS=(-1 --cycle --inline-info --ansi --height 40% --border --layout=reverse  --expect=/ --no-preview)
export FZF_TAB_OPTS=(-1 --cycle --inline-info --ansi --height 40% --border --layout=reverse  --expect=/ --priview '(bat --color=always {} || exa {}) 2> /dev/null | head -500'  --preview-window right:70%:noborder --color 'fg:#bbccdd,fg+:#ddeeff,bg:#334455,preview-bg:#223344,border:#778899')
