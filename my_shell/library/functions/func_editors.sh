# Desc: use which command to find out the file or command then open with editors
function editorw() {
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

function codew() {
    local COMMANDBIN=/usr/local/bin/code
    editorw $COMMANDBIN $1
}

function stw() {
    local COMMANDBIN=$HOME/bin/subl
    editorw $COMMANDBIN $1
}

function atomw() {
    local COMMANDBIN=/usr/local/bin/atom
    editorw $COMMANDBIN $1
}

# Desc: vim 编辑which命令找到的文件地址
function viw() {
    local COMMANDBIN=/usr/local/bin/vim
    editorw $COMMANDBIN $1
}

#   - Bypass fuzzy finder if there's only one match (--select-1)
#   - Exit if there's no match (--exit-0)
# Desc: Open the selected file with the default editor.
function fe() {
    local file
    file=$(fzf-tmux --query="$1" --select-1 --exit-0)
    [ -n "$file" ] && ${EDITOR:-vim} "$file"
}

# Desc: search ctags
function ftags() {
    local line
    [ -e tags ] &&
        line=$(
    awk 'BEGIN { FS="\t" } !/^!/ {print toupper($4)"\t"$1"\t"$2"\t"$3}' tags |
    cut -c1-80 | fzf --nth=1,2
    ) && $EDITOR $(cut -f3 <<< "$line") -c "set nocst" \
        -c "silent tag $(cut -f2 <<< "$line")"
}

# Desc: v - open files in ~/.viminfo
function v() {
    local files
    files=$(grep '^>' ~/.viminfo | cut -c3- |
    while read line; do
        [ -f "${line/\~/$HOME}" ] && echo "$line"
    done | fzf-tmux -d -m -q "$*" -1) && vim ${files//\~/$HOME}
}

#   - CTRL-O to open with `open` command,
#   - CTRL-E or Enter key to open with the $EDITOR
# Desc: Modified version where you can press
function fo() {
    local out file key
    out=$(fzf-tmux --query="$1" --exit-0 --expect=ctrl-o,ctrl-e)
    key=$(head -1 <<< "$out")
    file=$(head -2 <<< "$out" | tail -1)
    if [ -n "$file" ]; then
        [ "$key" = ctrl-o ] && open "$file" || ${EDITOR:-vim} "$file"
    fi
}

# Desc: fuzzy grep open via ag with line number
function vg() {
    local file
    local line

    read -r file line <<<"$(ag --nobreak --noheading $@ | fzf -0 -1 | awk -F: '{print $1, $2}')"

    if [[ -n $file ]]
    then
        vim $file +$line
    fi
}