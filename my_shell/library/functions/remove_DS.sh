# Desc: 删除.DS_Store文件
function removeDS() {
    if [ "" = "$1" ]; then
        find . -type f -name '*.DS_Store' -ls -delete
    else
        find $1 -type f -name '*.DS_Store' -ls -delete
    fi
}