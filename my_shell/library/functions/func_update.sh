function updotfiles() { # Desc: updotfiles:git 更新$MYRUNTIME 目录下的所有由git管理的目录
    upgitfiles
}

function upday() { # Desc: upday:每天一更新
    upruntimes
    upzshcustoms
    brew update  && brew upgrade && brew cleanup
    #gethosts
}

function upruntimes() { # Desc: upruntimes:git 更新$MYRUNTIME 目录下的所有由git管理的目录
    updotfiles
    upplugins
}

function upzshcustoms() { # Desc: upzshcustoms:git更新zsh自定义的文件
    upgitfiles $MYRUNTIME/oh-my-zsh/custom/plugins
    upgitfiles $MYRUNTIME/oh-my-zsh/antigen
#    upgitfiles $MYRUNTIME/oh-my-zsh/custom/themes/powerlevel9k
}

function upplugins() { # Desc: upplugins:git 更新 插件目录
    upgitfiles $MYRUNTIME/public
    customcd ~
}

