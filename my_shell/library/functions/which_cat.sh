# Desc: cat 打印which命令找到的文件地址
function catw() {
    cat `which "$1"`
}