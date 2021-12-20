function setproxy
    export HTTP_PROXY=http://127.0.0.1:7890;
    export HTTPS_PROXY=http://127.0.0.1:7890;
    export ALL_PROXY=socks5://127.0.0.1:7890;
end

function unsetproxy
    export HTTP_PROXY=;
    export HTTPS_PROXY=;
    export ALL_PROXY=;

end

function eproxy
    echo $HTTP_PROXY;
    echo $HTTPS_PROXY;
    echo $ALL_PROXY;
end
