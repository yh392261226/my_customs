function auto_change_netdisk_status() { # Desc: auto_change_netdisk_status:自动切换隐藏/显示 我的小米网盘中的特殊s文件夹
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
alias autonetdisk="auto_change_netdisk_status"

function show_useful_host() { # Desc: ii:display useful host related informaton
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
alias ii="show_useful_host"

function http_debug () { # Desc: http_debug:Download a web page and show info on what took time
    curl $@ -o /dev/null -w "dns: %{time_namelookup} connect: %{time_connect} pretransfer: %{time_pretransfer} starttransfer: %{time_starttransfer} total: %{time_total}\n" ;
}

function http_headers () { # Desc: http_headers:Grabs headers from web page
    curl -I -L $@ ;
}

function my_whois() { # Desc: mwhois:whois网址信息查询
    local domain=$(echo "$1" | awk -F/ '{print $3}') # get domain from URL
    if [ -z $domain ] ; then
    domain=$1
    fi
    echo "Getting whois record for: $domain …"

    /usr/bin/whois -h whois.internic.net $domain | sed '/NOTICE:/q'
}
alias mwhois="my_whois"

function flush_dns() { # Desc: flush_dns:刷新本地dns缓存
    sudo dscacheutil -flushcache
}
alias flushdns="flush_dns"

function set_proxy() { # Desc: set_proxy:设置命令行代理
    source $MYRUNTIME/tools/m_proxy
    export HTTP_PROXY=${local_http_proxy}; export HTTPS_PROXY=${local_https_proxy}; export ALL_PROXY=${local_all_proxy}
}
alias setproxy="set_proxy"

function unset_proxy() { # Desc: unset_proxy:取消设置命令行代理
    export HTTP_PROXY=""; export HTTPS_PROXY=""; export ALL_PROXY=""
}
alias unsetproxy="unset_proxy"

function get_proxy() { # Desc: get_proxy:获取命令行代理
    echo " \n
    HTTP_PROXY: $HTTP_PROXY\n
    HTTPS_PROXY: $HTTPS_PROXY\n
    ALL_PROXY: $ALL_PROXY\n
    \n
    \n
    " | cowsay | lolcat
}
alias getproxy="get_proxy"