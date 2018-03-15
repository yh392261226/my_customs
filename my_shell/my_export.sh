### 环境变量设定
export PLATFORM=$(uname -s)
export BASE=$HOME
export PATH="$(brew --prefix macvim)/bin:/usr/local/bin:$PATH"
export RBENV_ROOT=/usr/local/var/rbenv
export PATH="$(brew --prefix python3)/bin:$PATH"
export PATH="/usr/local/opt/python@2/libexec/bin:$HOME/.cargo/bin:/opt/local/bin:$PATH"
eval "$(rbenv init -)"

#####设置PATH变量
if [ "$MYSYSNAME" = "Mac" ]; then
    export PATH=/usr/local/bin:$PATH:/usr/local/var/rbenv/shims:/Users/json/go/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.cabal/bin:/usr/local/sbin:$HOME/bin:$(brew --prefix go)/bin:/usr/local/heroku/bin:$MYRUNTIME/customs/bin:/usr/local/opt/llvm/bin
    export PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"
    export PATH="$HOME/.Pokemon-Terminal:$PATH"
else
    export PATH=$PATH:/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin:/usr/local/sbin:/usr/local/rvm/bin:$HOME/.cabal/bin
fi

######设置editor
if [ "$MYSYSNAME" = "Mac" ]; then
    export EDITOR="$HOME/bin/subl"
elif [ "$MYSYSNAME" = "Ubuntu" ] || [ "$MYSYSNAME" = "Centos" ]; then
    export EDITOR="gedit"
fi

export GIT_MERGE_AUTOEDIT=no  #while git pull does not open merge editor
