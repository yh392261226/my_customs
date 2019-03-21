# Desc: ll 打印which命令找到的文件地址
function llw() {
    ls -l `which "$1"`
}