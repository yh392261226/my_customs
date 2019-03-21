# Desc: git更新zsh自定义的文件
function upzshcustoms() {
    upgitfiles $MYRUNTIME/oh-my-zsh/custom/plugins
    upgitfiles $MYRUNTIME/oh-my-zsh/antigen
    upgitfiles $MYRUNTIME/oh-my-zsh/custom/themes/powerlevel9k
}