# Desc:寻找当前目录下后缀名的所有文件
function lsext() {
    find . -type f -iname '*.'${1}'' -exec ls -l {} \; ;
}