function update_dotfiles
    update_git_files_and_modules
end

function update_today
    update_runtimes
    update_zsh_customs
    update_others
    zinit update
    brew update  && brew upgrade && brew cleanup
    #gethosts
end

function update_runtimes
    update_dotfiles
    update_plugins
end

function update_zsh_customs
    update_git_files_and_modules $MYRUNTIME/oh-my-zsh/custom/plugins
    update_git_files_and_modules $MYRUNTIME/oh-my-zsh/antigen
#    update_git_files_and_modules $MYRUNTIME/oh-my-zsh/custom/themes/powerlevel9k
end

function update_plugins
    update_git_files_and_modules $MYRUNTIME/public
    customcd ~
end

function update_others
    update_git_files_and_modules $MYRUNTIME/customs/others
    customcd ~
end

function update_go_tools
    source $MYRUNTIME/tools/m_proxy
    export HTTP_PROXY=${local_http_proxy}
    export HTTPS_PROXY=${local_https_proxy}
    export ALL_PROXY=${local_all_proxy}

    go install -v github.com/cweill/gotests/gotests@latest
    go install -v github.com/ramya-rao-a/go-outline@latest
    go install -v github.com/uudashr/gopkgs/v2/cmd/gopkgs@latest
    go install -v github.com/fatih/gomodifytags@latest
    go install -v github.com/josharian/impl@latest
    go install -v github.com/haya14busa/goplay/cmd/goplay@latest
    go install -v github.com/go-delve/delve/cmd/dlv@latest
    go install -v honnef.co/go/tools/cmd/staticcheck@latest
    go install -v golang.org/x/tools/gopls@latest
end


function update_command_theme
    curl -Lo $MYRUNTIME/bin/theme 'https://git.io/JM70M' 
    chmod +x $MYRUNTIME/bin/theme
end