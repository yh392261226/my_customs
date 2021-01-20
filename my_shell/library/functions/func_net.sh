function autodisk() { # Desc: 自动切换隐藏/显示 我的小米网盘中的特殊s文件夹
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

function ii() { # Desc: display useful host related informaton
    echo -e "\nYou are logged on ${RED}$HOST"
    echo -e "\nAdditionnal information:$NC " ; uname -a
    echo -e "\n${RED}Users logged on:$NC " ; w -h
    echo -e "\n${RED}Current date :$NC " ; date
    echo -e "\n${RED}Machine stats :$NC " ; uptime
    echo -e "\n${RED}Current network location :$NC " ; scselect
    echo -e "\n${RED}Public facing IP Address :$NC " ;curl myip.ipip.net
    #echo -e "\n${RED}DNS Configuration:$NC " ; scutil --dns
    echo
}

function httpDebug () { # Desc: Download a web page and show info on what took time
    curl $@ -o /dev/null -w "dns: %{time_namelookup} connect: %{time_connect} pretransfer: %{time_pretransfer} starttransfer: %{time_starttransfer} total: %{time_total}\n" ;
}

function httpHeaders () { # Desc: Grabs headers from web page
    curl -I -L $@ ;
}

function mwhois() { # Desc: whois网址信息查询
    local domain=$(echo "$1" | awk -F/ '{print $3}') # get domain from URL
    if [ -z $domain ] ; then
    domain=$1
    fi
    echo "Getting whois record for: $domain …"

    /usr/bin/whois -h whois.internic.net $domain | sed '/NOTICE:/q'
}

function flushdns() { # Desc: Flush dns
    sudo dscacheutil -flushcache
}

function setproxy() { # Desc: 设置命令行代理
    source $MYRUNTIME/tools/m_proxy
    export HTTP_PROXY=${local_http_proxy}; export HTTPS_PROXY=${local_https_proxy}; export ALL_PROXY=${local_all_proxy}
}

function unsetproxy() { # Desc: 取消设置命令行代理
    export HTTP_PROXY=""; export HTTPS_PROXY=""; export ALL_PROXY=""
}