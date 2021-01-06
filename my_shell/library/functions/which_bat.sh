# Desc: bat 打印which命令找到的文件地址
function batw() {
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        bat `which "$1"`
    else
        bat $(type "$1" | awk '{print $NF}')
    fi
}
