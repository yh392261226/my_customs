function remove_DS_files() { # Desc: remove_DS:删除.DS_Store文件
    if [ "" = "$1" ]; then
        find . -type f -name '*.DS_Store' -ls -delete
    else
        find $1 -type f -name '*.DS_Store' -ls -delete
    fi
}
alias remove_DS="remove_DS_files"

function remove_files_by_ext () { # Desc: remove_files_by_ext:删除后缀名为参数值的文件到回收站
    if [ "" = "$1" ]; then
        trash ./*
    else
        trash ./*$1
    fi
}
alias remove_ext="remove_files_by_ext"

function remove_ssh_tmp_file() { # Desc: remove_ssh_tmp_file:删除~/.ssh/tmp/*
    /bin/rm -f $HOME/.ssh/tmp/*
}
alias rmsshtmp="remove_ssh_tmp_file"
alias removesshtmp="remove_ssh_tmp_file"

function remove_to_trash () { # Desc: mtrash:删除到回收站
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
            /bin/mv "$path" ~/.Trash/"$dst"
        fi
    done
}
alias mtrash="remove_to_trash"

function trash () { # Desc: trash:Moves a file to the MacOS trash
    command /bin/mv "$@" ~/.Trash ;
}

function remove_whereis_file() { # Desc: remove_whereis_file:删除 which命令找到的文件
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ] && [ "$(type $1 | grep 'is an alias for')" = "" ]; then
        rm -f `which "$1"`
    else
        endfile=$(type "$@" | awk '{print $NF}')
        if [ -f $endfile ]; then
            rm -f $endfile
        else
            remove_whereis_file $endfile
        fi
    fi
}
alias removew="remove_whereis_file"
alias rmww="remove_whereis_file"