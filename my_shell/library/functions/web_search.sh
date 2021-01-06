#!/usr/bin/env bash
#Desc: 搜索引擎搜索 sbaidu|sgoogle keywords
SEARCH_BROWSER="/Applications/Safari.app"
[[ -d "/Applications/Google Chrome.app" ]] && SEARCH_BROWSER="/Applications/Google Chrome.app"

function sgoogle() {
    echo "open -a $SEARCH_BROWSER https://www.google.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "https://www.google.com/search?q= $1"；
}

function sbaidu() {
    echo "open -a $SEARCH_BROWSER https://www.baidu.com/s?wd= $1";
    open -a "$SEARCH_BROWSER" "https://www.baidu.com/s?wd= $1";
}

function sbing() {
    echo "open -a $SEARCH_BROWSER http://www.bing.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "http://www.bing.com/search?q= $1";
}

function syahoo() {
    echo "open -a $SEARCH_BROWSER http://www.yahoo.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "http://www.yahoo.com/search?q= $1";
}

function swikipedia() {
    echo "open -a $SEARCH_BROWSER http://en.wikipedia.org/wiki/Special:Search?search= $1";
    open -a "$SEARCH_BROWSER"  "http://en.wikipedia.org/wiki/Special:Search?search= $1";
}