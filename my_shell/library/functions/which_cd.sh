# Desc: cd 命令所在的文件夹
function cdw() {
    cd `dirname $(which "$1")`
}