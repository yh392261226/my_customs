function fzf_asdf_install
    # Desc: function: fzf_asdf_install:安装一个或多个版本的语言包 e.g. `vmi rust` # => fzf multimode, tab to mark, enter to install if no plugin is supplied (e.g. `vmi<CR>`), fzf will list them for you Mnemonic [V]ersion [M]anager [I]nstall
    set -l lang $argv

    if not test "$lang" = ""
        set -l lang (asdf plugin-list | fzf $FZF_CUSTOM_PARAMS --preview-window bottom:6:rounded:hidden:wrap --preview-label='[ 语言版本 ]' --header="$(_buildFzfHeader '' 'fzf_asdf_install')")
    end

    if test -n $lang
        set versions (asdf list-all $lang | fzf -m $FZF_CUSTOM_PARAMS --preview-window bottom:6:rounded:hidden:wrap --preview-label='[ 语言版本 ]' --header="$(_buildFzfHeader '' 'fzf_asdf_install')")
        if not test "$versions" = ""
            for v in (echo $versions)
                asdf install $lang $v
            end
        end
    end
end
alias fai="fzf_asdf_install"

function fzf_asdf_uninstall
    # Desc: function: fzf_asdf_uninstall:删除一个或多个版本的语言包 e.g. `vmi rust` # => fzf multimode, tab to mark, enter to remove if no plugin is supplied (e.g. `vmi<CR>`), fzf will list them for you Mnemonic [V]ersion [M]anager [C]lean
    set -l lang $argv

    if test -z $lang
        set lang (asdf plugin-list | fzf $FZF_CUSTOM_PARAMS --preview-window bottom:6:rounded:hidden:wrap --preview-label='[ 语言版本 ]' --header="$(_buildFzfHeader '' 'fzf_asdf_uninstall')")
    end

    if test -n $lang
        set versions (asdf list $lang | fzf -m $FZF_CUSTOM_PARAMS --preview-window bottom:6:rounded:hidden:wrap --preview-label='[ 语言版本 ]' --header="$(_buildFzfHeader '' 'fzf_asdf_uninstall')")
        if not test "$versions" = ""
            for v in (echo $versions)
                asdf uninstall $lang $v
            end
        end
    end
end
alias fau="fzf_asdf_uninstall"
