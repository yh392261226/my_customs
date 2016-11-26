### 环境变量设定
export PLATFORM=$(uname -s)
export BASE=$HOME
export PATH="$(brew --prefix macvim)/bin:/usr/local/bin:$PATH"
export RBENV_ROOT=/usr/local/var/rbenv
eval "$(rbenv init -)"

#####设置PATH变量
if [ "$MYSYSNAME" = "Mac" ]; then
    export PATH=/usr/local/bin:$PATH:/usr/local/var/rbenv/shims:/Users/json/go/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.cabal/bin:/usr/local/sbin:$HOME/bin:$(brew --prefix go)/bin:/usr/local/heroku/bin:$MYRUNTIME/customs/bin
else
    export PATH=$PATH:/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin:/usr/local/sbin:/usr/local/rvm/bin:$HOME/.cabal/bin
fi

######设置editor
if [ "$MYSYSNAME" = "Mac" ]; then
    export EDITOR="$HOME/bin/subl"
elif [ "$MYSYSNAME" = "Ubuntu" ] || [ "$MYSYSNAME" = "Centos" ]; then
    export EDITOR="gedit"
fi

