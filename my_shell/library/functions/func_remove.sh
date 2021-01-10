# Desc: 删除.DS_Store文件
function removeDS() {
    if [ "" = "$1" ]; then
        find . -type f -name '*.DS_Store' -ls -delete
    else
        find $1 -type f -name '*.DS_Store' -ls -delete
    fi
}

# Desc: 删除后缀名为参数值的文件到回收站
function rmext () {
    if [ "" = "$1" ]; then
        trash ./*
    else
        trash ./*$1
    fi
}

# Desc: 删除~/.ssh/tmp/*
function rmsshtmp() {
    /bin/rm -f $HOME/.ssh/tmp/*
}

# Desc: 删除到回收站
function mtrash () {
    local path
    for path in "$@"; do
        # ignore any arguments
        if [[ "$path" = -* ]]; then :
        else
            local dst=${path##*/}
            # append the time if necessary
            while [ -e ~/.Trash/"$dst" ]; do
                dst="$dst "$(date +%H-%M-%S)
            done
            mv "$path" ~/.Trash/"$dst"
        fi
    done
}

# Desc: Moves a file to the MacOS trash
function trash () { command mv "$@" ~/.Trash ; }     # trash:        Moves a file to the MacOS trash

# Desc: 删除 which命令找到的文件
function rmw() {
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        rm -f `which "$1"`
    else
        rm -f $(type "$1" | awk '{print $NF}')
    fi
}

