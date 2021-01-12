#!/usr/bin/env bash

SEARCH_BROWSER="/Applications/Safari.app"
[[ -d "/Applications/Google Chrome.app" ]] && SEARCH_BROWSER="/Applications/Google Chrome.app"

#Desc: GOOGLE搜索引擎搜索
function sgoogle() {
    echo "open -a $SEARCH_BROWSER https://www.google.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "https://www.google.com/search?q= $1"；
}

#Desc: 百度搜索引擎搜索
function sbaidu() {
    echo "open -a $SEARCH_BROWSER https://www.baidu.com/s?wd= $1";
    open -a "$SEARCH_BROWSER" "https://www.baidu.com/s?wd= $1";
}

#Desc: Bing搜索引擎搜索
function sbing() {
    echo "open -a $SEARCH_BROWSER http://www.bing.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "http://www.bing.com/search?q= $1";
}

#Desc: Yahoo搜索引擎搜索
function syahoo() {
    echo "open -a $SEARCH_BROWSER http://www.yahoo.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "http://www.yahoo.com/search?q= $1";
}

#Desc: wikipedia搜索引擎搜索
function swikipedia() {
    echo "open -a $SEARCH_BROWSER http://en.wikipedia.org/wiki/Special:Search?search= $1";
    open -a "$SEARCH_BROWSER"  "http://en.wikipedia.org/wiki/Special:Search?search= $1";
}

# Desc: 浏览器中打开网址
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

# Desc: 火狐浏览器打开网址
function firefox() {
    local BROWSERPATH="/Applications/Firefox.app"
    browser $BROWSERPATH $1
}

# Desc: Safari浏览器中打开网址
function safari() {
    local BROWSERPATH="/Applications/Safari.app"
    browser $BROWSERPATH $1
}

# Desc: Chrome浏览器中打开网址
function chrome() {
    local BROWSERPATH="/Applications/Google Chrome.app"
    browser $BROWSERPATH $1
}

# Desc:隐身Chrome浏览器打开网址
function stealth-browser() {
    local MYRUNTIME=$(cat $HOME/.myruntime)
    local DEFAULTBROWSER="/Applications/Google Chrome.app"
    [[ -f $MYRUNTIME/tools/m_proxy ]] && source $MYRUNTIME/tools/m_proxy
    [[ -d "$DEFAULTBROWSER" ]] && open  "/Applications/Google Chrome.app" --args -proxy-server=socks5://${ip}:${port} --incognito
}

# Desc: c - 列出Chrome浏览器的历史
function c() {
    local cols sep
    export cols=$(( COLUMNS / 3 ))
    export sep='{::}'

    cp -f ~/Library/Application\ Support/Google/Chrome/Default/History /tmp/h
    sqlite3 -separator $sep /tmp/h \
        "select title, url from urls order by last_visit_time desc" |
    ruby -ne '
    cols = ENV["cols"].to_i
    title, url = $_.split(ENV["sep"])
    len = 0
    puts "\x1b[36m" + title.each_char.take_while { |e|
    if len < cols
        len += e =~ /\p{Han}|\p{Katakana}|\p{Hiragana}|\p{Hangul}/ ? 2 : 1
    end
    }.join + " " * (2 + cols - len) + "\x1b[m" + url' |
    fzf --ansi --multi --no-hscroll --tiebreak=index |
    sed 's#.*\(https*://\)#\1#' | xargs open
}

# Desc: buku数据库配合fzf列出网址收藏
fb() {
    # save newline separated string into an array
    mapfile -t website <<< "$(buku -p -f 5 | column -ts$'\t' | fzf --multi)"

    # open each website
    for i in "${website[@]}"; do
        index="$(echo "$i" | awk '{print $1}')"
        buku -p "$index"
        buku -o "$index"
    done
}

# Desc: 打开goodfon.ru
function goodfon() {
    local DEFAULTBROWSER="/Applications/Firefox.app"      #default browser for open goodfon
    local SECONDBROWSER="/Applications/Google Chrome.app" #second browser for open goodfon
    local URL="https://www.goodfon.ru/"

    if [ "$1" = "" ]; then
        [[ -d "$DEFAULTBROWSER" ]] && /usr/bin/open -a "$DEFAULTBROWSER" "$URL"
    fi

    if [ "$1" = "chrome" ] || [ "$1" = "google" ]; then
        [[ -d "$SECONDBROWSER" ]] && /usr/bin/open -a "$SECONDBROWSER" "$URL"
    fi
}
