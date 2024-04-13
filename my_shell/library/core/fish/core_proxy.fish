set switcher 0
if test -f $MYRUNTIME/tools/m_proxy_fish
    source $MYRUNTIME/tools/m_proxy_fish
end
if test "$switcher" = "1"
    set -gx http_proxy $local_http_proxy
    set -gx https_proxy $local_https_proxy
    set -gx ALL_PROXY $local_all_proxy
end

function setproxy
    set -gx HTTP_PROXY $local_http_proxy
    set -gx HTTPS_PROXY $local_https_proxy
    set -gx ALL_PROXY $local_all_proxy
end
alias onproxy "setproxy"

function unsetproxy
    set -gx HTTP_PROXY ''
    set -gx HTTPS_PROXY ''
    set -gx ALL_PROXY ''

end
alias offproxy "unsetproxy"

function eproxy
    echo "HTTP_PROXY: $HTTP_PROXY";
    echo "HTTPS_PROXY: $HTTPS_PROXY";
    echo "ALL_PROXY: $ALL_PROXY";
end

function pproxy
    echo "HTTP_PROXY: $HTTP_PROXY";
    echo "HTTPS_PROXY: $HTTPS_PROXY";
    echo "ALL_PROXY: $ALL_PROXY";
end
