# Desc: ll 打印which命令找到的文件地址
function llw() {
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        ls -l  `which "$1"`
    else
        ls -l  $(type "$1" | awk '{print $NF}')
    fi
}