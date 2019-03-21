# Desc: vim 编辑which命令找到的文件地址
function viw() {
    vim `which "$1"`
}