if test "fish" = "$nowshell"
    function __fzfmenu__
        set cmd "fd -tf --max-depth=1"
        eval $cmd | $MYRUNTIME/customs/bin/fzfmenu
    end

    function __fzf-menu__
        set -l LBUFFER "$LBUFFER"(__fzfmenu__)
        set ret $status
        zle reset-prompt
        return $ret
    end

    commandline -f -e __fzf-menu__ '^T^G'
    bind -M vicmd '^T^G' __fzf-menu__
    bind -M viins '^T^G' __fzf-menu__
end
