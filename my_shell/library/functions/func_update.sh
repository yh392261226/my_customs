# Desc: git 更新$MYRUNTIME 目录下的所有由git管理的目录
function updotfiles() {
    upgitfiles
}

# Desc: 每天一更新
function upday() {
    upruntimes
    upzshcustoms
    brew update  && brew upgrade && brew cleanup
    #gethosts
}

# Desc: git 更新$MYRUNTIME 目录下的所有由git管理的目录
function upruntimes() {
    updotfiles
    upplugins
}

# Desc: git更新zsh自定义的文件
function upzshcustoms() {
    upgitfiles $MYRUNTIME/oh-my-zsh/custom/plugins
    upgitfiles $MYRUNTIME/oh-my-zsh/antigen
#    upgitfiles $MYRUNTIME/oh-my-zsh/custom/themes/powerlevel9k
}

# Desc: git 更新 插件目录
function upplugins() {
    upgitfiles $MYRUNTIME/public
    customcd ~
}

