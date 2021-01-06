# Desc: open 打开which命令找到的目录或文件
function openw() {
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        open `dirname $(which "$1")`
    else
        open $(dirname $(type "$1" | awk '{print $NF}'))
    fi
}
