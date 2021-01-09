# Desc: cat 打印which命令找到的文件地址
function catw() {
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        cat `which "$1"`
    else
        cat $(type "$1" | awk '{print $NF}')
    fi
}

# Desc: bat 打印which命令找到的文件地址
function batw() {
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        bat `which "$1"`
    else
        bat $(type "$1" | awk '{print $NF}')
    fi
}

# Desc: Opens any file in MacOS Quicklook Preview
function ql () { qlmanage -p "$*" >& /dev/null; }    # ql:           Opens any file in MacOS Quicklook Preview

