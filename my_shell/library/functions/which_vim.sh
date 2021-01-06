# Desc: vim 编辑which命令找到的文件地址
function viw() {
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        vim `which "$1"`
    else
        vim $(type "$1" | awk '{print $NF}')
    fi
}