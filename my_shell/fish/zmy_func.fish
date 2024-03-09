function setproxy
    export HTTP_PROXY=http://127.0.0.1:7890;
    export HTTPS_PROXY=http://127.0.0.1:7890;
    export ALL_PROXY=socks5://127.0.0.1:7890;

    export HTTP_PROXY=http://127.0.0.1:58591;
    export HTTPS_PROXY=http://127.0.0.1:58591;
    export ALL_PROXY=socks5://127.0.0.1:51837;
end
alias onproxy="setproxy"

function unsetproxy
    export HTTP_PROXY=;
    export HTTPS_PROXY=;
    export ALL_PROXY=;

end
alias offproxy="unsetproxy"

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
