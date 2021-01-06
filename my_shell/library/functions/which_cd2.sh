# Desc: cd 命令所在的文件夹
function cdto() {
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        cd `dirname $(which "$1")`
    else
        cd $(dirname $(type "$1" | awk '{print $NF}'))
    fi
}