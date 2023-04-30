#!/usr/bin/env fish

set SEARCH_BROWSER "/Applications/Safari.app"
if test -d "/Applications/Google Chrome.app"
    set SEARCH_BROWSER "/Applications/Google Chrome.app"
end

function sgoogle
    echo "open -a $SEARCH_BROWSER https://www.google.com/search?q= $argv";
    open -a "$SEARCH_BROWSER" "https://www.google.com/search?q= $argv"；
end
alias google="sgoogle"  # Desc: alias: google:sgoogle命令的别名

function sbaidu
    echo "open -a $SEARCH_BROWSER https://www.baidu.com/s?wd= $argv";
    open -a "$SEARCH_BROWSER" "https://www.baidu.com/s?wd= $argv";
end
alias baidu="sbaidu"    # Desc: alias: baidu:sbaidu命令的别名

function sbing
    echo "open -a $SEARCH_BROWSER http://www.bing.com/search?q= $argv";
    open -a "$SEARCH_BROWSER" "http://www.bing.com/search?q= $argv";
end
alias bing="sbing"      # Desc: alias: bing:sbing命令的别名

function syahoo
    echo "open -a $SEARCH_BROWSER http://www.yahoo.com/search?q= $argv";
    open -a "$SEARCH_BROWSER" "http://www.yahoo.com/search?q= $argv";
end
alias yahoo="syahoo"        # Desc: alias: yahoo:syahoo命令的别名

function swikipedia
    echo "open -a $SEARCH_BROWSER http://en.wikipedia.org/wiki/Special:Search?search= $argv";
    open -a "$SEARCH_BROWSER"  "http://en.wikipedia.org/wiki/Special:Search?search= $argv";
end
alias wikipedia="swikipedia"    # Desc: alias: wikipedia:swikipedia命令的别名

function browser
    set BROWSERPATH $argv[1]
    set DEFAULTURL "https://www.google.com/"
    if test ! -d "$BROWSERPATH/"
        echo "Does not found Firefox "
        exit 1
    end

    if test "" = "$argv[2]" 
        set url $DEFAULTURL
    else
        set url $argv[2]
    end

    if test ! -f $url
        if [ $url[0..6] != "http://"] -a [ $url[0..7] != "https://" ]
            set url "http://$url"
        end
    end
    /usr/bin/open -a "$BROWSERPATH" "$url"
end
alias browse="browser"      # Desc: alias: browse:browser命令的别名

function firefox
    set BROWSERPATH "/Applications/Firefox.app"
    browser $BROWSERPATH $argv
end

function safari
    set BROWSERPATH "/Applications/Safari.app"
    browser $BROWSERPATH $argv
end

function chrome
    set BROWSERPATH "/Applications/Google Chrome.app"
    browser $BROWSERPATH $argv
end

function brave
    set BROWSERPATH "/Applications/Brave Browser.app"
    browser $BROWSERPATH $argv
end

function stealth-browser
    set MYRUNTIME $(cat $HOME/.myruntime)
    set DEFAULTBROWSER "/Applications/Google Chrome.app"
    if test -f $MYRUNTIME/tools/m_proxy
        source $MYRUNTIME/tools/m_proxy
    end
    if test -d "$DEFAULTBROWSER"
        open  "/Applications/Google Chrome.app" --args -proxy-server=socks5://$ip:$port --incognito
    end
end
alias sb="stealth-browser"      # Desc: alias: sb:stealth-browser命令的别名

function chromium_history
    if test "" = "$argv[1]"
        echo "Does not send param!"
        return 1
    end
    set cols sep
    export cols ( COLUMNS / 3 )
    export sep '{::}'
    rm -f /tmp/h
    cp -r -f "$argv[1]" /tmp/h
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
    sed 's#.*\(https*://\)#\1#' | xargs open -a "$argv[2]"
end
alias ch="chromium_history"     # Desc: alias: ch:chromium_history命令的别名

function chrome_default_history
    chromium_history ~/Library/Application\ Support/Google/Chrome/Default/History "/Applications/Google Chrome.app"
end
alias c="chrome_default_history"    # Desc: alias: c:chrome_default_history命令的别名

function chrome_profile1_history
    chromium_history ~/Library/Application\ Support/Google/Chrome/Profile\ 1/History "/Applications/Google Chrome.app"
end
alias c2="chrome_profile1_history"      # Desc: alias: c2:chrome_profile1_history命令的别名

function brave_default_history
    chromium_history ~/Library/Application\ Support/BraveSoftware/Brave-Browser/Default/History "/Applications/Brave Browser.app"
end
alias bh="brave_default_history"    # Desc: alias: bh:brave_default_history命令的别名

function chromium_bookmarks
    if test "" = "$argv[1]"
        echo "Does not send param!"
        return 1
    else
        rm -f /tmp/bookmarks
        cp -r -f "$argv[1]" /tmp/bookmarks
    end

     set jq_script '
        def ancestors: while(. | length >= 2; del(.[-1,-2]));
        . as $in | paths(.url?) as $key | $in | getpath($key) | {name,url, path: [$key[0:-2] | ancestors as $a | $in | getpath($a) | .name?] | reverse | join("/") } | .path + "/" + .name + "\t" + .url'

    jq -r "$jq_script" < /tmp/bookmarks \
        | sed -E 's/(.*)\t(.*)/\\1\t\x1b[36m\\2\x1b[m/g' \
        | fzf --ansi \
        | cut -d'\t' -f2 \
        | xargs open -a "$argv[2]"
end
alias cb="chromium_bookmarks"   # Desc: alias: cb:chromium_bookmarks命令的别名

function chrome_default_bookmarks
    chromium_bookmarks ~/Library/Application\ Support/Google/Chrome/Default/Bookmarks "/Applications/Google Chrome.app"
end
alias cb1="chrome_default_bookmarks"    # Desc: alias: cb1:chrome_default_bookmarks命令的别名

function chrome_profile1_bookmarks
    chromium_bookmarks ~/Library/Application\ Support/Google/Chrome/Profile\ 1/Bookmarks "/Applications/Google Chrome.app"
end
alias cb2="chrome_profile1_bookmarks"       # Desc: alias: cb2:chrome_profile1_bookmarks命令的别名

function brave_default_bookmarks
    chromium_bookmarks ~/Library/Application\ Support/BraveSoftware/Brave-Browser/Default/Bookmarks "/Applications/Brave Browser.app"
end
alias bb="brave_default_bookmarks"      # Desc: alias: bb:brave_default_bookmarks命令的别名

# function fzf_mark_by_buku
#     # save newline separated string into an array
#     mapfile -t website <<< "$(buku -p -f 5 | column -ts$'\t' | fzf --multi)"

#     # open each website
#     for i in "${website[@]}"
#         set index "$(echo "$i" | awk '{print $1}')"
#         buku -p "$index"
#         buku -o "$index"
#     end
# end
# alias fb="fzf_mark_by_buku"     # Desc: alias: fb:fzf_mark_by_buku命令的别名

function goodfon
    set DEFAULTBROWSER "/Applications/Firefox.app"      #default browser for open goodfon
    set SECONDBROWSER "/Applications/Google Chrome.app" #second browser for open goodfon
    set URL "https://www.goodfon.ru/"

    if test "$argv" = ""
        if test -d "$DEFAULTBROWSER"
            /usr/bin/open -a "$DEFAULTBROWSER" "$URL"
        end
    end

    if test "$argv" = "chrome" -o "$argv" = "google"
        if test -d "$SECONDBROWSER"
            /usr/bin/open -a "$SECONDBROWSER" "$URL"
        end
    end
end
alias gf="goodfon"      # Desc: alias: gf:goodfon命令的别名

function _checkDirFull
    if test "" != "$1"
        set maxsize 2000
        set picpath $(dirname $1)
        set cursize $(ls $picpath | wc -l)

        if test "$cursize" -ge "$maxsize"
            set curcount $(echo $picpath | tr -cd "[0-9]")
            set tmpmiddlecount $curcount
            set curcount (so$curcount+1)
            if test $curcount -le 9
                set curcount 0$curcount
            end
            set prefixpath $(echo $picpath | sed "s,$tmpmiddlecounts,,g")
            set newpath "$prefixpath$curcount"
            if test ! -d $newpath
                mkdir $newpath
            end
            mv $argv $newpath/$(basename $argv)
            echo "$argv $newpath/$(basename $argv)"
        end
    end
end

function autoDiffDownloadPicureByName
    ##图片文件夹路径
    set PICPATH $(cat ~/.picpath)
    set MYRUNTIME $(cat $HOME/.myruntime)
    ##数据库文件路径
    set DBFILE $MYRUNTIME/tools/pictures_db.log
    ##去重文件数据库文件路径（仅有文件名）
    set FULLFILENAMESDB $MYRUNTIME/tools/pictures_fullfilenames_db.log
    set COMMANDBIN sqlite3
    set FULLFILENAMESDB2 $MYRUNTIME/tools/fullfilenames_db.log.sqlitedb
    set IFSHOWTHUMB 0
    set RECORDTYPE 0
    set msg ""

    if test "" != "$argv[1]"
        set IFSHOWTHUMB $argv[1]
    end
    if test "" != "$argv[2]"
        set RECORDTYPE $argv[2]
    end

    set curprocessid $fish_pids
    #调起后台脚本，监控火狐浏览器状态，如果浏览器进程消失，则杀死下面的进程
    set tmpshell $(mktemp)
    if test -f $tmpshell
        echo "#!/usr/bin/env bash\n" > $tmpshell
        echo "curfierfoxcounts=1\n" >> $tmpshell
        echo "while [ \"\$curfierfoxcounts\" -gt \"0\" ]; do\n" >> $tmpshell
        echo "    curfierfoxcounts=\$(ps -ef | grep 'Firefox.app/Contents/MacOS/firefox' | grep -v grep | wc -l)\n" >> $tmpshell
        echo "    sleep 1\n" >> $tmpshell
        echo "done\n" >> $tmpshell
        echo "if [ \"\$curfierfoxcounts\" -lt \"1\" ]; then\n" >> $tmpshell
        echo "    ps -ef | grep \"fswatch -0 \$PICPATH\" | grep -v grep | awk '{print \$2}' | xargs kill\n" >> $tmpshell
        echo "fi\n" >> $tmpshell
    end
    bash $tmpshell > /dev/null 2>&1 &

    if test ! -f $FULLFILENAMESDB2
        set SQL "CREATE TABLE pictures ('id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 'pic_name' TEXT DEFAULT NULL, 'created_at' DATETIME NOT NULL DEFAULT CURRENT_TIME, 'pic_path' TEXT DEFAULT NULL);"
        $COMMANDBIN $SQL $FULLFILENAMESDB2
    end

    fswatch -0 $PICPATH | while read -d "" event; do
        if [ "$(ps -ef | grep 'Firefox.app/Contents/MacOS/firefox' | grep -v grep | wc -l)" -gt "0" ]
            set fullfilename $event
            set filename (basename $fullfilename)
            set showtype 0
            if [ "0" = "$RECORDTYPE" ]; then
                if [ "$(grep -w $filename $FULLFILENAMESDB)" != "" ]
                    set tmpresult (find $PICPATH/ -type f -name "$filename"  | grep -v "$fullfilename" | wc -l)
                    if [ "$tmpresult" -gt "1" ]
                        set msg "Already deleted ..."
                        trash $fullfilename
                    end
                else
                    echo $filename >> $FULLFILENAMESDB
                    set msg "Already recorded ..."
                    set showtype 1
                    echo $fullfilename >> $DBFILE
                end
            else if [ "1" = "$RECORDTYPE" ]
                if test ! -f $FULLFILENAMESDB2
                    echo "The sqlite db file does not exists !"
                    return 1
                end
                set SQL "select * from pictures where pic_name = '"$filename"';"
                set tmpresult ($COMMANDBIN $SQL $FULLFILENAMESDB2)
                if [ "$tmpresult" != "" ]
                    set tmpresult (find $PICPATH/ -type f -name "$filename"  | grep -v "$fullfilename" | wc -l)
                    if [ "$tmpresult" -gt "1" ]
                        set msg "Already deleted ..."
                        trash $fullfilename
                    end
                else
                    set tmp_path (dirname $fullfilename)
                    set SQL 'insert into pictures (pic_name, pic_path) values ("'"$filename"'", "'"$tmp_path"'");'
                    $COMMANDBIN $SQL $FULLFILENAMESDB2
                    set msg "Already recorded ..."
                    set showtype 1
                    echo $fullfilename >> $DBFILE
                end
            end
            echo $msg
            _checkDirFull $fullfilename #存放目录满的情况下自动生成目录并迁移新文件
            if [ "$IFSHOWTHUMB" -eq "1" ] -a [ "$showtype" -eq "1" ]
                #展示图片
                printf '\033]1337;File=inline=1;width=20%%;preserveAspectRatio=0'
                printf ":"
                base64 < "$fullfilename"
                printf '\a\n'
            end
        end
    end
    rm -f $tmpshell
    ps -ef | grep "fswatch -0 $PICPATH" | grep -v grep | awk '{print $2}' | xargs kill > /dev/null
end

function goodfonWithAutoDiff
    goodfon
    autoDiffDownloadPicureByName
end
alias gfa="goodfonWithAutoDiff"     # Desc: alias: gfa:goodfonWithAutoDiff命令的别名

function goodfonWithAutoDiff2
    goodfon
    autoDiffDownloadPicureByName 0 1
end
alias gfa2="goodfonWithAutoDiff2"   # Desc: alias: gfa2:goodfonWithAutoDiff2命令的别名

