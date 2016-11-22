#[antigen]  一个zsh的插件管理
source "$ZSH/antigen/antigen.zsh"
antigen use oh-my-zsh
antigen bundle heroku
antigen bundle pip
antigen bundle lein
antigen bundle command-not-found
#load antigen theme
antigen theme robbyrussell
antigen-bundle arialdomartini/oh-my-git
antigen-apply
source $MYRUNTIME/oh-my-git/prompt.sh
