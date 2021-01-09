# Desc: open url in browsers
function browser() {
    local BROWSERPATH=$1
    local DEFAULTURL="https://www.google.com/"
    [[ ! -d "$BROWSERPATH/" ]] && echo "Does not found Firefox " && exit 1

    [ "" = "$2" ] && url=$DEFAULTURL || url=$2

    if [ ! -f $url ]; then
        if [ "${url:0:6}" != "http://" ] && [ "${url:0:7}" != "https://" ]; then
            url="http://$url"
        fi
    fi
    /usr/bin/open -a "$BROWSERPATH" "$url"
}

function firefox() {
    local BROWSERPATH="/Applications/Firefox.app"
    browser $BROWSERPATH $1
}

function safari() {
    local BROWSERPATH="/Applications/Safari.app"
    browser $BROWSERPATH $1
}

function chrome() {
    local BROWSERPATH="/Applications/Google Chrome.app"
    browser $BROWSERPATH $1
}

# Desc:隐身浏览器Chrome
function stealth-browser() {
    local MYRUNTIME=$(cat $HOME/.myruntime)
    local DEFAULTBROWSER="/Applications/Google Chrome.app"
    [[ -f $MYRUNTIME/tools/m_proxy ]] && source $MYRUNTIME/tools/m_proxy
    [[ -d "$DEFAULTBROWSER" ]] && open  "/Applications/Google Chrome.app" --args -proxy-server=socks5://${ip}:${port} --incognito
}