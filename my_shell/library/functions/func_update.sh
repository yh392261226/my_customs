function updotfiles() { # Desc: git 更新$MYRUNTIME 目录下的所有由git管理的目录
    upgitfiles
}

function upday() { # Desc: 每天一更新
    upruntimes
    upzshcustoms
    brew update  && brew upgrade && brew cleanup
    #gethosts
}

function upruntimes() { # Desc: git 更新$MYRUNTIME 目录下的所有由git管理的目录
    updotfiles
    upplugins
}

function upzshcustoms() { # Desc: git更新zsh自定义的文件
    upgitfiles $MYRUNTIME/oh-my-zsh/custom/plugins
    upgitfiles $MYRUNTIME/oh-my-zsh/antigen
#    upgitfiles $MYRUNTIME/oh-my-zsh/custom/themes/powerlevel9k
}

function upplugins() { # Desc: git 更新 插件目录
    upgitfiles $MYRUNTIME/public
    customcd ~
}

