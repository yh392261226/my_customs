# Desc: 删除 which命令找到的文件
function rmw() {
    rm -f `which "$1"`
}