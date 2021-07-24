function editorw() { # Desc: editorw:use which command to find out the file or command then open with editors
    local COMMANDBIN=$1
    local FILENAME=$2
    if [ -f $COMMANDBIN ]; then
        if [ "" != "$FILENAME" ]; then
            command -v "$@" > /dev/null 2>&1
            [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
            if [ "$(type $FILENAME | grep 'a shell function from')" = "" ]; then
                $COMMANDBIN `which "$FILENAME"`
            else
                $COMMANDBIN  $(type "$FILENAME" | awk '{print $NF}')
            fi
        else
            $COMMANDBIN `pwd`
        fi
    else
        echo "$COMMANDBIN does not exsits !!!"
        return 1
    fi
}

function codew() { # Desc: codew:visual studio code 编辑which命令找到的文件地址
    local COMMANDBIN=/usr/local/bin/code
    editorw $COMMANDBIN $1
}

function stw() { # Desc: stw:sublime text 编辑which命令找到的文件地址
    local COMMANDBIN=$HOME/bin/subl
    editorw $COMMANDBIN $1
}

function atomw() { # Desc: atomw:atom 编辑which命令找到的文件地址
    local COMMANDBIN=/usr/local/bin/atom
    editorw $COMMANDBIN $1
}

function viw() { # Desc: viw:vim 编辑which命令找到的文件地址
    if [ -f /usr/local/bin/vim ]; then
        local COMMANDBIN=/usr/local/bin/vim
    elif [ -f /opt/homebrew/bin/vim ]; then
        local COMMANDBIN=/opt/homebrew/bin/vim
    fi
    editorw $COMMANDBIN $1
}

function nviw() { # Desc: nviw:neovim 编辑which命令找到的文件地址
    if [ -f /usr/local/bin/nvim ]; then
        local COMMANDBIN=/usr/local/bin/nvim
    elif [ -f /opt/homebrew/bin/nvim ]; then
        local COMMANDBIN=/usr/local/bin/nvim
    fi
    editorw $COMMANDBIN $1
}

function fzf_e() { # Desc: fzf_e:Open the selected file with the default editor. Bypass fuzzy finder if there's only one match (--select-1) Exit if there's no match (--exit-0)
    local file
    file=$(fzf-tmux --query="$1" --select-1 --exit-0)
    [ -n "$file" ] && ${EDITOR:-vim} "$file"
}

function fe() { # Desc: fe:Open the selected file with the default editor. Bypass fuzzy finder if there's only one match (--select-1) Exit if there's no match (--exit-0)
    fzf_e $@
}

function fzf_tags() { # Desc: ftags:search ctags
    local line
    [ -e tags ] &&
        line=$(
    awk 'BEGIN { FS="\t" } !/^!/ {print toupper($4)"\t"$1"\t"$2"\t"$3}' tags |
    cut -c1-80 | fzf --nth=1,2
    ) && $EDITOR $(cut -f3 <<< "$line") -c "set nocst" \
        -c "silent tag $(cut -f2 <<< "$line")"
}

function ftags() { # Desc: ftags:search ctags
    fzf_tags $@
}

function v() { # Desc: v:open files in ~/.viminfo
    local files
    files=$(grep '^>' ~/.viminfo | cut -c3- |
    while read line; do
        [ -f "${line/\~/$HOME}" ] && echo "$line"
    done | fzf-tmux -d -m -q "$*" -1) && vim ${files//\~/$HOME}
}

function fzf_o() { # Desc: fzf_o:Modified version where you can press CTRL-O to open with `open` command, CTRL-E or Enter key to open with the $EDITOR
    local out file key
    out=$(fzf-tmux --query="$1" --exit-0 --expect=ctrl-o,ctrl-e)
    key=$(head -1 <<< "$out")
    file=$(head -2 <<< "$out" | tail -1)
    if [ -n "$file" ]; then
        [ "$key" = ctrl-o ] && open "$file" || ${EDITOR:-vim} "$file"
    fi
}

function fo() { # Desc: fo:Modified version where you can press CTRL-O to open with `open` command, CTRL-E or Enter key to open with the $EDITOR
    fzf_o $@
}

function vg() { # Desc: vg:fuzzy grep open via ag with line number
    local file
    local line

    read -r file line <<<"$(ag --nobreak --noheading $@ | fzf -0 -1 | awk -F: '{print $1, $2}')"

    if [[ -n $file ]]
    then
        vim $file +$line
    fi
}
