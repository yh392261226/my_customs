function fzf_linux_command_searcher
    set MDDIR $MYRUNTIME/customs/others/linux-command
    if not test -d $MDDIR
        echo "请先下载https://github.com/jaywcjlove/linux-command?tab=readme-ov-file#命令行工具"
        return 1
    end

    ls $MDDIR/command | fzf $FZF_CUSTOM_PARAMS +m --height=90% --bind="enter:become(glow --style=dark $MDDIR/command/{})" --bind="ctrl-y:execute-silent(echo {} | awk -F'.' '{print \$1}' | pbcopy)+abort" --header=(_buildFzfHeader '' 'fzf_linux_command_searcher') --preview="glow --style=dark -p $MDDIR/command/{}"
end
alias flc="fzf_linux_command_searcher"

function fzf_how_to_cook_searcher
    set MDDIR $MYRUNTIME/customs/others/HowToCook
    if not test -d $MDDIR
        echo "请先下载https://github.com/Anduin2017/HowToCook/tree/master"
        return 1
    end

    set TMPCOOKBOOK (mktemp)
    find $MDDIR/dishes -type f -name '*.md' > $TMPCOOKBOOK
    if not test -f $TMPCOOKBOOK
        echo '未生成缓存文件...'
        return 1
    end

    cat $TMPCOOKBOOK | awk -F'/' '{print $NF}' | awk -F'.' '{print $1}' | fzf $FZF_CUSTOM_PARAMS +m --height=90% --bind="enter:become($MYRUNTIME/customs/bin/_markdown_previewer {} $TMPCOOKBOOK)" --bind="ctrl-y:execute-silent(echo {} | pbcopy)+abort" --header=(_buildFzfHeader '' 'fzf_how_to_cook_searcher') --preview=" $MYRUNTIME/customs/bin/_markdown_previewer {} $TMPCOOKBOOK "
end
alias fh2c="fzf_how_to_cook_searcher"

function fzf_develop_references_searcher
    set MDDIR $MYRUNTIME/customs/others/reference
    if not test -d $MDDIR
        echo "请先下载https://github.com/jaywcjlove/reference"
        return 1
    end

    ls $MDDIR/docs | fzf $FZF_CUSTOM_PARAMS +m --height=90% --bind="enter:become(glow --style=dark $MDDIR/docs/{})" --bind="ctrl-y:execute-silent(echo $MDDIR/docs/{} | pbcopy)+abort" --header=(_buildFzfHeader '' 'fzf_develop_references_searcher') --preview="glow --style=dark -p $MDDIR/docs/{}"
end
alias fdrs="fzf_develop_references_searcher"