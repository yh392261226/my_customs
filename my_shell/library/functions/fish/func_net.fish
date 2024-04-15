### Package Desc: 网络相关命令

function auto_change_netdisk_status
    # Desc: function: auto_change_netdisk_status:自动切换隐藏/显示 我的小米网盘中的特殊s文件夹
    set CPATH /Volumes/XiaoMi/下载/
    set CNAME over_s

    if not test -d $CPATH
        echo "请先链接小米路由器，并挂载小米路由盘！！！"
        return 1
    end

    if test -d $CPATH/$CNAME
        mv $CPATH/$CNAME $CPATH/.$CNAME
    else if test -d $CPATH/.$CNAME
        mv $CPATH/.$CNAME $CPATH/$CNAME
    end
end
alias acns="auto_change_netdisk_status"

function show_useful_host
    # Desc: function: show_useful_host:Display useful host related informaton
    echo -e "\nYou are logged on $HOST"
    echo -e "\nAdditionnal information: " ; uname -a
    echo -e "\nUsers logged on: " ; w -h
    echo -e "\nCurrent date : " ; date
    echo -e "\nMachine stats : " ; uptime
    echo -e "\nCurrent network location : " ; scselect
    echo -e "\nPublic facing IP Address : " ; curl myip.ipip.net
    #echo -e "\nDNS Configuration: " ; scutil --dns
    echo
end
alias uh="show_useful_host"

function http_debug
    # Desc: function: http_debug: Download a web page and show info on what took time
    curl $argv -o /dev/null -w "dns: %{time_namelookup} connect: %{time_connect} pretransfer: %{time_pretransfer} starttransfer: %{time_starttransfer} total: %{time_total}\n"
end
alias hdebug="http_debug"

function http_headers
    # Desc: function: http_headers:Grabs headers from web page
    curl -I -L $argv
end
alias hheaders="http_headers"

function custom_whois
    # Desc: function: custom_whois:Whois网址信息查询
    set domain (echo "$argv" | awk -F/ '{print $3}') # get domain from URL
    if test -z $domain
        set domain $argv
    end
    echo "Getting whois record for: $domain …"

    /usr/bin/whois -h whois.internic.net $domain | sed '/NOTICE:/q'
end
alias cwhois="custom_whois"

function flush_dns
    # Desc: function: flush_dns:刷新本地dns缓存
    sudo dscacheutil -flushcache
end
alias fdns="flush_dns"

function set_proxy
    # Desc: function: set_proxy:设置命令行代理
    source $MYRUNTIME/tools/m_proxy_fish
    set -xg HTTP_PROXY $local_http_proxy
    set -xg HTTPS_PROXY $local_https_proxy
    set -xg ALL_PROXY $local_all_proxy
end
alias setproxy="set_proxy"
alias onproxy="set_proxy"

function proxy_port_config
    # Desc: function: configproxy:设置proxy代理端口
    nvim $MYRUNTIME/tools/m_proxy_fish
end
alias vproxy="proxy_port_config"

function proxy_port_cat
    # Desc: function: proxy_port_cat:察看proxy代理设置
    cat $MYRUNTIME/tools/m_proxy_fish
end
alias cproxy="proxy_port_cat"

function unset_proxy
    # Desc: function: unset_proxy:取消设置命令行代理
    set -e HTTP_PROXY
    set -e HTTPS_PROXY
    set -e ALL_PROXY
end
alias uproxy="unset_proxy"
alias offproxy="unset_proxy"

function print_proxy
    # Desc: function: print_proxy:输出命令行代理
    echo "http: $HTTP_PROXY"
    echo "https: $HTTPS_PROXY"
    echo "All: $ALL_PROXY"
end
alias pproxy="print_proxy"

function get_proxy
    # Desc: function: get_proxy:获取命令行代理
    echo "HTTP_PROXY: $HTTP_PROXY"
    echo "HTTPS_PROXY: $HTTPS_PROXY"
    echo "ALL_PROXY: $ALL_PROXY"
end
alias gproxy="get_proxy"

function get_port_using_status
    # Desc: function: get_port_using_status:获取端口占用情况
    if not test "$argv" = ""
        set -l param "$argv"
    else
        set -l param ":"
    end
    lsof -P -i -n | grep $argv
end
alias gps="get_port_using_status"

function list_ports
    # Desc: function: list_ports:获取所有正在使用的端口
    lsof -P -i -n | less
end
alias lps="list_ports"
