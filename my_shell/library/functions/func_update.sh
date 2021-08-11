function update_dotfiles() { # Desc: update_dotfiles:git 更新$MYRUNTIME 目录下的所有由git管理的目录
    update_git_files_and_modules
}

function update_today() { # Desc: upday:每天一更新
    update_runtimes
    update_zsh_customs
    brew update  && brew upgrade && brew cleanup
    #gethosts
}

function update_runtimes() { # Desc: update_runtimes:git 更新$MYRUNTIME 目录下的所有由git管理的目录
    update_dotfiles
    upplugins
}

function update_zsh_customs() { # Desc: update_zsh_customs:git更新zsh自定义的文件
    update_git_files_and_modules $MYRUNTIME/oh-my-zsh/custom/plugins
    update_git_files_and_modules $MYRUNTIME/oh-my-zsh/antigen
#    update_git_files_and_modules $MYRUNTIME/oh-my-zsh/custom/themes/powerlevel9k
}

function update_plugins() { # Desc: upplugins:git 更新 插件目录
    update_git_files_and_modules $MYRUNTIME/public
    customcd ~
}

