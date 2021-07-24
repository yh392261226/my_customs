function remove_DS() { # Desc: remove_DS:删除.DS_Store文件
    if [ "" = "$1" ]; then
        find . -type f -name '*.DS_Store' -ls -delete
    else
        find $1 -type f -name '*.DS_Store' -ls -delete
    fi
}

function remove_ext () { # Desc: remove_ext:删除后缀名为参数值的文件到回收站
    if [ "" = "$1" ]; then
        trash ./*
    else
        trash ./*$1
    fi
}

function remove_sshtmp() { # Desc: remove_sshtmp:删除~/.ssh/tmp/*
    /bin/rm -f $HOME/.ssh/tmp/*
}

function mtrash () { # Desc: mtrash:删除到回收站
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

function trash () { # Desc: trash:Moves a file to the MacOS trash
    command mv "$@" ~/.Trash ;
}

function remove_w() { # Desc: remove_w:删除 which命令找到的文件
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        rm -f `which "$1"`
    else
        rm -f $(type "$1" | awk '{print $NF}')
    fi
}

