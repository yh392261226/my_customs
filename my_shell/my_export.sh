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
[[ -d $HOME/.cargo/bin ]] && export PATH="$PATH:$HOME/.cargo/bin"

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

### M1 sqlite3
if [ -d /opt/homebrew/opt/sqlite/bin ]; then
	export PATH="/opt/homebrew/opt/sqlite/bin:$PATH"
	export LDFLAGS="-L/opt/homebrew/opt/sqlite/lib"
	export CPPFLAGS="-I/opt/homebrew/opt/sqlite/include"
	export PKG_CONFIG_PATH="/opt/homebrew/opt/sqlite/lib/pkgconfig"
fi

#wine 不输出debug信息
export WINEDEBUG=-all
export MYCUSTOMS=$MYRUNTIME/customs
export MYTOOLS=$MYRUNTIME/tools
export MYSHELL=$MYCUSTOMS/my_shell
export MYBIN=$MYCUSTOMS/bin
