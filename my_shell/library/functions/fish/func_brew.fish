function brew_clean_caches
    # Desc: function: brew_clean_caches:Brew Delete (one or multiple) Caches files of  mnemonic (e.g. uninstall)
    set -l current_dir (pwd)
    cd (brew --cache)
    find . -maxdepth 1 -type f -exec rm -f {} +
    cd (brew --cache)/downloads
    find . -maxdepth 1 -type f -exec rm -f {} +
    echo "Common files already deleted, You have to clean other files manually!!!"
    cd $current_dir
end
alias bcc="brew_clean_caches"

function fzf_brew_delete_by_select
    # Desc: function: fzf_brew_delete_by_select:Brew Delete (one or multiple) selected application(s) mnemonic (e.g. uninstall)
    set uninst (brew leaves | fzf -m $FZF_CUSTOM_PARAMS --preview='brew info {1} | bat --color=always --language=Markdown --style=plain' --header="$(_buildFzfHeader '' 'fzf_brew_delete_by_select')")

    if not test "$uninst" = ""
        for prog in (echo $uninst)
            brew uninstall $prog
        end
    end
end
alias fbd="fzf_brew_delete_by_select"

function fzf_brew_update_by_select
    # Desc: function: fzf_brew_update_by_select:Brew Update (one or multiple) selected application(s) mnemonic [B]rew [U]pdate [P]lugin
    set upd (brew leaves | fzf -m $FZF_CUSTOM_PARAMS --preview='brew info {1} | bat --color=always --language=Markdown --style=plain' --header="$(_buildFzfHeader '' 'fzf_brew_update_by_select')")

    if not test "$upd" = ""
        set upd (echo $upd | sed 's/\n/ /g')
        brew upgrade $upd
    end
end
alias fbup="fzf_brew_update_by_select"

function fzf_brew_upgrade_by_select
    # Desc: function: fzf_brew_upgrade_by_select:Brew upgrade (one or multiple)
    set upgrads (brew outdated | fzf -m $FZF_CUSTOM_PARAMS --preview='brew info {1} | bat --color=always --language=Markdown --style=plain' --header="$(_buildFzfHeader '' 'fzf_brew_upgrade_by_select')")
    if not test "$upgrads" = ""
        set upgrades (echo $upgrads | sed 's/\n/ /g')
        brew upgrade $upgrades
    end
end
alias fbug="fzf_brew_upgrade_by_select"

function reinstall_neovim
    # Desc: function: reinstall_neovim:重新安装neovim
    brew reinstall neovim --HEAD
end
alias renvim="reinstall_neovim"

function fzf_brew_install_by_select
    # Desc: function: fzf_brew_install_by_select:Brew Install (one or multiple) selected application(s) using "brew search" as source input mnemonic [B]rew [I]nstall [P]lugin
    set inst (brew search | fzf -m $FZF_CUSTOM_PARAMS \
        --preview='brew info {1} | bat --color=always --language=Markdown --style=plain' \
        --header=(_buildFzfHeader '' 'fzf_brew_install_by_select'))

    if not test "$inst" = ""
        for prog in (echo $inst)
            brew install $prog
        end
    end
end
alias fbis="fzf_brew_install_by_select"
