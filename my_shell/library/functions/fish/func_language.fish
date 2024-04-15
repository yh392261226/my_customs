### Package Desc: 语言相关命令

function fzf_rvm_select
    # Desc: function: fzf_rvm_select:RVM integration
    # echo system
    set rb (rvm list | grep ruby | cut -c 4- | awk '{print $1}' | fzf-tmux $FZF_CUSTOM_PARAMS --preview='$MYRUNTIME/customs/bin/_previewer_fish {}' --header="$(_buildFzfHeader '' 'fzf_rvm_select')" -l 30 +m --reverse)
    and rvm use $rb
end
alias frs="fzf_rvm_select"

function gems
    # Desc: function: gems:Rvm多个版本的gem操作同一个包
    for v in 2.0.0 1.8.7 jruby 1.9.3
        rvm use $v
        gem $argv
    end
end

function rakes
    # Desc: function: rakes:rvm多个版本的rake操作同一个包
    for v in 2.0.0 1.8.7 jruby 1.9.3
        rvm use $v
        rake $argv
    end
end

function php_change_version
    # Desc: function: php_change_version:PHP依赖于brew切换已安装版本
    echo "*******************************************************"
    echo "Current version is : "
    php -v
    echo "*******************************************************"
    echo ""
    echo "Select to change version:"
    set installedPhpVersions (brew ls --versions | ggrep -E 'php(@.*)?\s' | ggrep -oP '(?<=\s)\d\.\d' | uniq | sort)

    set tmpfile (mktemp)
    for phpVersion in $installedPhpVersions
        echo "brew unlink php@$phpVersion;" >> $tmpfile
    end

    set choose (printf "%s\n" $installedPhpVersions | fzf $FZF_CUSTOM_PARAMS --preview " echo php@{} " --header="$(_buildFzfHeader '' 'php_change_version')" --bind 'ctrl-y:execute-silent(echo -n php@{}| pbcopy)+abort')
    if test "" = "$choose"
        echo "Action abort !"
        return 1
    else
        echo "brew link php@$choose;" >> $tmpfile
    end
    bash $tmpfile &> /dev/null
    php -v
    trap 'rm -f "$tmpfile"'
    echo "Now, it's done ..."
end
alias pcv="php_change_version"

function shell_debug
    # Desc: function: shell_debug:依赖shellcheck对shell脚本debug
    if test -f /usr/local/bin/shellcheck
        /usr/local/bin/shellcheck $argv
    else
        echo "shellcheck does not exsits !"
    end
end
alias sdebug="shell_debug"
