#!/usr/bin/env bash
#Desc: 搜索引擎搜索 cbaidu|cgoogle keywords
SEARCH_BROWSER="/Applications/Safari.app"
[[ -d "/Applications/Google Chrome.app" ]] && SEARCH_BROWSER="/Applications/Google Chrome.app"

function cgoogle() {
    echo "open -a $SEARCH_BROWSER https://www.google.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "https://www.google.com/search?q= $1"；
}

function cbaidu() {
    echo "open -a $SEARCH_BROWSER https://www.baidu.com/s?wd= $1";
    open -a "$SEARCH_BROWSER" "https://www.baidu.com/s?wd= $1";
}

function bing() {
    echo "open -a $SEARCH_BROWSER http://www.bing.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "http://www.bing.com/search?q= $1";
}

function yahoo() {
    echo "open -a $SEARCH_BROWSER http://www.yahoo.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "http://www.yahoo.com/search?q= $1";
}

function wikipedia() {
    echo "open -a $SEARCH_BROWSER http://en.wikipedia.org/wiki/Special:Search?search= $1";
    open -a "$SEARCH_BROWSER"  "http://en.wikipedia.org/wiki/Special:Search?search= $1";
}