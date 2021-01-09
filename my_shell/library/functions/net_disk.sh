# Desc: 自动切换隐藏/显示 我的特殊s文件夹
function autodisk() {
    CPATH=/Volumes/XiaoMi/下载/
    CNAME=over_s

    if [ ! -d $CPATH ]; then
        echo "请先链接小米路由器，并挂载小米路由盘！！！"
        return 1
    fi

    if [ -d $CPATH/$CNAME ]; then
        mv $CPATH/$CNAME $CPATH/.$CNAME
    elif [ -d $CPATH/.$CNAME ]; then
        mv $CPATH/.$CNAME $CPATH/$CNAME
    fi
}