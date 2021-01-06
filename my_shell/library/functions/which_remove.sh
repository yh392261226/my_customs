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