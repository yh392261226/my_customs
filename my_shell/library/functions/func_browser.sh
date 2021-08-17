#!/usr/bin/env bash

SEARCH_BROWSER="/Applications/Safari.app"
[[ -d "/Applications/Google Chrome.app" ]] && SEARCH_BROWSER="/Applications/Google Chrome.app"

function sgoogle() { #Desc: sgoogle:GOOGLE搜索引擎搜索
    echo "open -a $SEARCH_BROWSER https://www.google.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "https://www.google.com/search?q= $1"；
}

function sbaidu() { #Desc: sbaidu:百度搜索引擎搜索
    echo "open -a $SEARCH_BROWSER https://www.baidu.com/s?wd= $1";
    open -a "$SEARCH_BROWSER" "https://www.baidu.com/s?wd= $1";
}

function sbing() { #Desc: sbing:Bing搜索引擎搜索
    echo "open -a $SEARCH_BROWSER http://www.bing.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "http://www.bing.com/search?q= $1";
}

function syahoo() { #Desc: syahoo:Yahoo搜索引擎搜索
    echo "open -a $SEARCH_BROWSER http://www.yahoo.com/search?q= $1";
    open -a "$SEARCH_BROWSER" "http://www.yahoo.com/search?q= $1";
}

function swikipedia() { #Desc: syahoo:wikipedia搜索引擎搜索
    echo "open -a $SEARCH_BROWSER http://en.wikipedia.org/wiki/Special:Search?search= $1";
    open -a "$SEARCH_BROWSER"  "http://en.wikipedia.org/wiki/Special:Search?search= $1";
}

function browser() { # Desc: browser:浏览器中打开网址
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

function firefox() { # Desc: firefox:火狐浏览器打开网址
    local BROWSERPATH="/Applications/Firefox.app"
    browser $BROWSERPATH $1
}

function safari() { # Desc: safari:Safari浏览器中打开网址
    local BROWSERPATH="/Applications/Safari.app"
    browser $BROWSERPATH $1
}

function chrome() { # Desc: chrome:Chrome浏览器中打开网址
    local BROWSERPATH="/Applications/Google Chrome.app"
    browser $BROWSERPATH $1
}

function stealth-browser() { # Desc: stealth-browser:隐身Chrome浏览器打开网址
    local MYRUNTIME=$(cat $HOME/.myruntime)
    local DEFAULTBROWSER="/Applications/Google Chrome.app"
    [[ -f $MYRUNTIME/tools/m_proxy ]] && source $MYRUNTIME/tools/m_proxy
    [[ -d "$DEFAULTBROWSER" ]] && open  "/Applications/Google Chrome.app" --args -proxy-server=socks5://${ip}:${port} --incognito
}

function chrome_history() { # Desc: chrome_history:列出Chrome浏览器的历史
    if [ "" = "$@" ]; then
        echo "Does not send param!"
        return 1
    fi
    local cols sep
    export cols=$(( COLUMNS / 3 ))
    export sep='{::}'
    rm -f /tmp/h
    cp -r -f $@ /tmp/h
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

function chrome_default_history() { # Desc: chrome_default_history:列出Chrome默认账户的浏览器的历史
    chrome_history ~/Library/Application\ Support/Google/Chrome/Default/History
}
alias c="chrome_default_history"

function chrome_profile1_history() { # Desc: chrome_profile1_history:列出Chrome Profile 1账户的浏览器的历史
    chrome_history ~/Library/Application\ Support/Google/Chrome/Profile\ 1/History
}
alias c2="chrome_profile1_history"

function fzf_mark_by_buku() { # Desc: fzf_mark_by_buku:buku数据库配合fzf列出网址收藏
    # save newline separated string into an array
    mapfile -t website <<< "$(buku -p -f 5 | column -ts$'\t' | fzf --multi)"

    # open each website
    for i in "${website[@]}"; do
        index="$(echo "$i" | awk '{print $1}')"
        buku -p "$index"
        buku -o "$index"
    done
}
alias fb="fzf_mark_by_buku"

function goodfon() { # Desc: goodfon:打开goodfon.ru
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
alias gf="goodfon"

function autoDiffDownloadPicureByName() { # Desc:利用fswatch监控目录，通过比对文件名，实现自动去重下载的图片
    ##图片文件夹路径
    local PICPATH=$HOME/Pictures/down_pics/
    ##数据库文件路径
    local DBFILE=$PICPATH/db.log
    ##去重文件数据库文件路径（仅有文件名）
    local FULLFILENAMESDB=$PICPATH/fullfilenames_db.log
    local IFSHOWTHUMB=0
    local msg=""

    [[ "" != "$1" ]] && IFSHOWTHUMB=1

    curprocessid=$$
    #调起后台脚本，监控火狐浏览器状态，如果浏览器进程消失，则杀死下面的进程
    tmpshell=$(mktemp)
    # echo $tmpshell
    if [ -f $tmpshell ]; then
        echo "#!/usr/bin/env bash\n" > $tmpshell
        echo "curfierfoxcounts=1\n" >> $tmpshell
        echo "while [ \"\$curfierfoxcounts\" -gt \"0\" ]; do\n" >> $tmpshell
        echo "    curfierfoxcounts=\$(ps -ef | grep 'Firefox.app/Contents/MacOS/firefox' | grep -v grep | wc -l)\n" >> $tmpshell
        echo "    sleep 1\n" >> $tmpshell
        echo "done\n" >> $tmpshell
        echo "if [ \"\$curfierfoxcounts\" -lt \"1\" ]; then\n" >> $tmpshell
        echo "    ps -ef | grep \"fswatch -0 \$PICPATH\" | grep -v grep | awk '{print \$2}' | xargs kill\n" >> $tmpshell
        echo "fi\n" >> $tmpshell
    fi
    bash $tmpshell > /dev/null 2>&1 &

    fswatch -0 $PICPATH | while read -d "" event; do
        if [ "$(ps -ef | grep 'Firefox.app/Contents/MacOS/firefox' | grep -v grep | wc -l)" -gt "0" ]; then
            fullfilename=${event}
            filename=$(basename $fullfilename)
            showtype=0

            if [ "$(grep -w $filename $FULLFILENAMESDB)" != "" ]; then
                tmpresult=$(find $PICPATH/ -type f -name "$filename"  | grep -v "$fullfilename" | wc -l)
                if [ "$tmpresult" -gt "1" ]; then
                    msg="Already deleted ..."
                    trash $fullfilename
                fi
            else
                echo $filename >> $FULLFILENAMESDB
                msg="Already recorded ..."
                showtype=1
                echo $fullfilename >> $DBFILE
            fi

            echo $msg
            if [ "$IFSHOWTHUMB" -eq "1" ] && [ "$showtype" -eq "1" ]; then
                #展示图片
                printf '\033]1337;File=inline=1;width=20%%;preserveAspectRatio=0'
                printf ":"
                base64 < "$fullfilename"
                printf '\a\n'
            fi
        fi
    done
    rm -f $tmpshell
    ps -ef | grep "fswatch -0 $PICPATH" | grep -v grep | awk '{print $2}' | xargs kill > /dev/null
}

function goodfonWithAutoDiff() { # Desc: 打开goodfon.ru后 通过目录监控自动过滤重名文件
    goodfon
    autoDiffDownloadPicureByName $@
}
alias gfa="goodfonWithAutoDiff"
