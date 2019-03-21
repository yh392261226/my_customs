# Desc: cd 命令所在的文件夹
function cdto() {
    cd `dirname $(which "$1")`
}