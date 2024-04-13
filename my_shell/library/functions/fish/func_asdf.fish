function fzf_asdf_install
    # Desc: function: fzf_asdf_install:安装一个或多个版本的语言包 e.g. `vmi rust` # => fzf multimode, tab to mark, enter to install if no plugin is supplied (e.g. `vmi<CR>`), fzf will list them for you Mnemonic [V]ersion [M]anager [I]nstall
    set lang $argv[1]

    if test -z $lang
        set lang (asdf plugin-list | fzf $FZF_CUSTOM_PARAMS --preview-window bottom:6:rounded:hidden:wrap --preview-label='[ 语言版本 ]' --header="$(_buildFzfHeader '' 'fzf_asdf_install')")
    end

    if test -n $lang
        set versions (asdf list-all $lang | fzf -m $FZF_CUSTOM_PARAMS --preview-window bottom:6:rounded:hidden:wrap --preview-label='[ 语言版本 ]' --header="$(_buildFzfHeader '' 'fzf_asdf_install')")
        if test -n $versions
            for version in (echo $versions)
                asdf install $lang $version
            end
        end
    end
end

alias fai fzf_asdf_install # Desc: alias: fai:fzf_asdf_install命令的别名

function fzf_asdf_uninstall
    # Desc: function: fzf_asdf_uninstall:删除一个或多个版本的语言包 e.g. `vmi rust` # => fzf multimode, tab to mark, enter to remove if no plugin is supplied (e.g. `vmi<CR>`), fzf will list them for you Mnemonic [V]ersion [M]anager [C]lean
    set lang $argv[1]

    if test -z $lang
        set lang (asdf plugin-list | fzf $FZF_CUSTOM_PARAMS --preview-window bottom:6:rounded:hidden:wrap --preview-label='[ 语言版本 ]' --header="$(_buildFzfHeader '' 'fzf_asdf_uninstall')")
    end

    if test -n $lang
        set versions (asdf list $lang | fzf -m $FZF_CUSTOM_PARAMS --preview-window bottom:6:rounded:hidden:wrap --preview-label='[ 语言版本 ]' --header="$(_buildFzfHeader '' 'fzf_asdf_uninstall')")
        if test -n $versions
            for version in (echo $versions)
                asdf uninstall $lang $version
            end
        end
    end
end

alias fau fzf_asdf_uninstall # Desc: alias: fau:fzf_asdf_uninstall命令的别名
