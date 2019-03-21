# Desc: 删除后缀名为参数值的文件到回收站
function rmext () {
    if [ "" = "$1" ]; then
        trash ./*
    else
        trash ./*$1
    fi
}