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