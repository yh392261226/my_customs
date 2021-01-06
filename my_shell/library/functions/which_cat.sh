# Desc: cat 打印which命令找到的文件地址
function catw() {
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        cat `which "$1"`
    else
        cat $(type "$1" | awk '{print $NF}')
    fi
}