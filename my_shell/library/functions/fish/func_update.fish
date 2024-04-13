function update_dotfiles
    update_git_files_and_modules
end
alias ud="update_dotfiles"

function update_today
    update_runtimes
    update_zsh_customs
    update_others
    zinit update
    brew update; and brew upgrade; and brew cleanup
    #gethosts
end
alias update="update_today"
alias ut="update_today"

function update_runtimes
    update_dotfiles
    update_plugins
end
alias ur="update_runtimes"

function update_zsh_customs
    update_git_files_and_modules $MYRUNTIME/oh-my-zsh/custom/plugins
    update_git_files_and_modules $MYRUNTIME/oh-my-zsh/antigen
    # update_git_files_and_modules $MYRUNTIME/oh-my-zsh/custom/themes/powerlevel9k
end
alias uzc="update_zsh_customs"

function update_plugins
    update_git_files_and_modules $MYRUNTIME/public
    customcd ~
end
alias ugp="update_plugins"

function update_others
    update_git_files_and_modules $MYRUNTIME/customs/others
    customcd ~
end
alias uo="update_others"

function update_go_tools
    source $MYRUNTIME/tools/m_proxy_fish
    set -x HTTP_PROXY $local_http_proxy
    set -x HTTPS_PROXY $local_https_proxy
    set -x ALL_PROXY $local_all_proxy

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
alias ugt="update_go_tools"

function update_command_theme
    curl -Lo $MYRUNTIME/bin/theme 'https://git.io/JM70M'; and chmod +x $MYRUNTIME/bin/theme
end
alias uct="update_command_theme"
