# Desc: 获取命令所在目录
function dirw() {
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        echo $(dirname "$@");
    else
        echo $(dirname $(type "$@" | awk '{print $NF}'));
    fi
}