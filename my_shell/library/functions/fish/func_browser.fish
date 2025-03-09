set SEARCH_BROWSER "/Applications/Safari.app"
# [ -d "/Applications/Google Chrome.app" ]; and set SEARCH_BROWSER "/Applications/Google Chrome.app"

function search_by_github
    if not test "$argv" = ""
    echo 'test'
        echo "open -a $SEARCH_BROWSER https://github.com/search?type=repositories&q=$argv"
        open -a "$SEARCH_BROWSER" "https://github.com/search?type=repositories&q=$argv"
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text :")
        else
            read -P "Type search text: " text
        end
        open -a "$SEARCH_BROWSER" "https://github.com/search?type=repositories&q=$text"
    end
end
alias github="search_by_github"

function search_by_google
    if not test "$argv" = ""
        echo "open -a $SEARCH_BROWSER https://www.google.com/search?q=$argv"
        open -a "$SEARCH_BROWSER" "https://www.google.com/search?q=$argv"
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text")
        else
            read -P "Type search text: " text
        end
        open -a "$SEARCH_BROWSER" "https://www.google.com/search?q=$text"
    end
end
alias google="search_by_google"

function search_by_baidu
    if not test "$argv" = ""
        echo "open -a $SEARCH_BROWSER https://www.baidu.com/s?wd=$argv"
        open -a "$SEARCH_BROWSER" "https://www.baidu.com/s?wd=$argv"
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text")
        else
            read -P "Type search text: " text
        end
        open -a "$SEARCH_BROWSER" "https://www.baidu.com/s?wd=$text"
    end
end
alias baidu="search_by_baidu"

function search_by_bing
    if not test "$argv" = ""
        echo "open -a $SEARCH_BROWSER http://www.bing.com/search?q=$argv"
        open -a "$SEARCH_BROWSER" "http://www.bing.com/search?q=$argv"
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text")
        else
            read -P "Type search text: " text
        end
        open -a "$SEARCH_BROWSER" "http://www.bing.com/search?q=$text"
    end
end
alias bing="search_by_bing"

function search_by_yahoo
    if not test "$argv" = ""
        echo "open -a $SEARCH_BROWSER http://www.yahoo.com/search?q=$argv"
        open -a "$SEARCH_BROWSER" "http://www.yahoo.com/search?q=$argv"
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text")
        else
            read -P "Type search text: " text
        end
        open -a "$SEARCH_BROWSER" "http://www.yahoo.com/search?q=$text"
    end
end
alias yahoo="search_by_yahoo"

function search_by_wikipedia
    if not test "$argv" = ""
        echo "open -a $SEARCH_BROWSER http://en.wikipedia.org/wiki/Special:Search?search=$argv"
        open -a "$SEARCH_BROWSER" "http://en.wikipedia.org/wiki/Special:Search?search=$argv"
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text")
        else
            read -P "Type search text: " text
        end
        open -a "$SEARCH_BROWSER" "http://en.wikipedia.org/wiki/Special:Search?search=$text"
    end
end
alias wikipedia="search_by_wikipedia"

function open_in_browser
    set BROWSERPATH $argv[1]
    set DEFAULTURL "https://www.google.com/"
    test ! -d "$BROWSERPATH/"
    and echo "Does not found Firefox "
    and return 1

    if test -z $argv[2]
        set url $DEFAULTURL
    else
        set url $argv[2]
    end

    if not test -f $url
        if not string match -q -r '^https?://' $url
            set url "http://$url"
        end
    end
    /usr/bin/open -a "$BROWSERPATH" "$url"
end
alias browse="open_in_browser"

function firefox
    set BROWSERPATH "/Applications/Firefox.app"
    open_in_browser $BROWSERPATH $argv[1]
end

function safari
    set BROWSERPATH "/Applications/Safari.app"
    open_in_browser $BROWSERPATH $argv[1]
end

function chrome
    set BROWSERPATH "/Applications/Google Chrome.app"
    open_in_browser $BROWSERPATH $argv[1]
end

function brave
    set BROWSERPATH "/Applications/Brave Browser.app"
    open_in_browser $BROWSERPATH $argv[1]
end

function stealth-browser
    set MYRUNTIME (cat $HOME/.myruntime)
    set DEFAULTBROWSER "/Applications/Google Chrome.app"
    test -f $MYRUNTIME/tools/m_proxy_fish; and source $MYRUNTIME/tools/m_proxy_fish
    test -d "$DEFAULTBROWSER"
    and open "/Applications/Google Chrome.app" --args -proxy-server=socks5://$ip:$port --incognito
end
alias sb="stealth-browser"

function fzf_safari_history
    sqlite3 $HOME/Library/Safari/History.db "SELECT datetime(h.visit_time + 978307200, 'unixepoch', 'localtime') as date, i.url FROM history_visits h INNER JOIN history_items i ON h.history_item = i.id" | fzf --ansi --multi --no-hscroll --tiebreak=index $FZF_CUSTOM_PARAMS \
        --preview ' echo -n {} | awk -F"|" "{print \$2}"' \
        --bind 'focus:transform-preview-label:echo -n "{}" | awk -F "|" "{print \"[\" \$1 \"]\"}"' \
        --bind "ctrl-y:execute-silent(echo {} | grep -Eo 'https?://[^[:space:]]+' | pbcopy)+abort" \
        --bind "enter:execute(echo {} | grep -Eo 'https?://[^[:space:]]+' | head -1 | xargs open)+abort" \
        --header="$(_buildFzfHeader '' 'fzf_safari_history')"
end
alias fsh="fzf_safari_history"

function fzf_safari_bookmarks
    plutil -convert xml1 -o - $HOME/Library/Safari/Bookmarks.plist | grep -E '<string>http[s]?://|<string>.*</string>' | sed -E 's/<string>(http[s]?:\/\/[^<]*)<\/string>/\1/g' | grep -B 1 "http[s]\{0,1\}" | sed -E 's/<string>([^<]*)<\/string>/\1/g' | sed 's/^--$/|seprator|/g' | sed 's/^[[:space:]]*//g' | sed 's/^$/No title .../g' | tr '\n' ' ' | sed 's/|seprator|/\n/g' | fzf --ansi --multi --no-hscroll --tiebreak=index $FZF_CUSTOM_PARAMS \
        --preview ' echo -n {}' \
        --bind 'focus:transform-preview-label:echo -n {} ' \
        --bind 'ctrl-y:execute-silent(echo {} | grep -E "http[s]?://.*" | pbcopy)+abort' \
        --bind "enter:execute(echo {} | grep -Eo 'https?://[^[:space:]]+' | head -1 | xargs open)+abort" \
        --header="$(_buildFzfHeader '' 'fzf_safari_bookmarks')"
end
alias fsb="fzf_safari_bookmarks"

function chromium_history
    if test -z $argv[1]
        echo "Does not send param!"
        return 1
    end
    set cols (math $COLUMNS / 3)
    set sep '   '
    rm -f /tmp/h
    cp -r -f $argv[1] /tmp/h
    sqlite3 -separator $sep /tmp/h "select title, url from urls order by last_visit_time desc" | fzf --ansi --multi --no-hscroll --tiebreak=index --delimiter="$sep" $FZF_CUSTOM_PARAMS \
        --preview ' echo -n {2} ' \
        --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' \
        --bind 'ctrl-y:execute-silent(echo {2} | pbcopy)+abort' \
        --header="$(_buildFzfHeader '' 'chromium_history')" \
    | awk -F "$sep" '{print $2}' \
    | xargs -n 1 open -a (echo $argv[2])
end
alias ch="chromium_history"


function chrome_default_history
    chromium_history $HOME/Library/Application\ Support/Google/Chrome/Default/History '/Applications/Google Chrome.app'
end
alias cdh="chrome_default_history"

function chrome_profile1_history
    chromium_history $HOME/Library/Application\ Support/Google/Chrome/Profile\ 1/History "/Applications/Google Chrome.app"
end
alias cph="chrome_profile1_history"

function brave_default_history
    chromium_history $HOME/Library/Application\ Support/BraveSoftware/Brave-Browser/Default/History "/Applications/Brave Browser.app"
end
alias bdh="brave_default_history"

function browser_history_manage
    while true
        set -l action (printf "%s\n" \
            "🔎 Safari" \
            "🔎 Chrome_Default" \
            "🔎 Chrome_Profile1" \
            "🔎 Brave_Default" \
            "🚪 退出系统" | \
            fzf --header " 浏览器历史记录管理系统 " \
                --prompt "主菜单 ❯ " \
                --preview-window=up:30% \
                --preview "echo '选择操作类型'" \
                --height=15% \
                --header="$(_buildFzfHeader '' 'browser_history_manage')" \
                --reverse)

        switch "$action"
            case '*Safari*'
                fzf_safari_history
            case '*Chrome_Default*'
                chrome_default_history
            case '*Chrome_Profile1*'
                chrome_profile1_history
            case '*Brave_Default*'
                brave_default_history
            case '*退出系统*'
                return
        end
    end
end

alias bh="browser_history_manage"
bind -M insert ˙ browser_history_manage

function chromium_bookmarks
    if test -z $argv[1]
        echo "Does not send param!"
        return 1
    else
        rm -f /tmp/bookmarks
        cp -r -f $argv[1] /tmp/bookmarks
    end

    set jq_script '
        def ancestors: while(. | length >= 2; del(.[-1,-2]));
        . as $in | paths(.url?) as $key | $in | getpath($key) | {name,url, path: [$key[0:-2] | ancestors as $a | $in | getpath($a) | .name?] | reverse | join("/") } | .path + "/" + .name + "\t" + .url'

    jq -r "$jq_script" < /tmp/bookmarks \
    | sed -E "s/(.*)\t(.*)/\\1\t\x1b[36m\\2\x1b[m/g" \
    | fzf --ansi $FZF_CUSTOM_PARAMS \
          --bind 'focus:transform-preview-label:echo -n \"[ {1} ]\";' \
          --bind 'ctrl-y:execute-silent(echo {} | grep -Eo \"https?://[^[:space:]]+\" | pbcopy)+abort' \
          --header="$(_buildFzfHeader '' 'chromium_bookmarks')" \
    | cut -d '	' -f2 \
    | xargs open -a (echo $argv[2])
end
alias cb="chromium_bookmarks"

function chrome_default_bookmarks
    chromium_bookmarks $HOME/Library/Application\ Support/Google/Chrome/Default/Bookmarks "/Applications/Google Chrome.app"
end
alias cdb="chrome_default_bookmarks"

function chrome_profile1_bookmarks
    chromium_bookmarks $HOME/Library/Application\ Support/Google/Chrome/Profile\ 1/Bookmarks "/Applications/Google Chrome.app"
end
alias cpb="chrome_profile1_bookmarks"

function brave_default_bookmarks
    chromium_bookmarks $HOME/Library/Application\ Support/BraveSoftware/Brave-Browser/Default/Bookmarks "/Applications/Brave Browser.app"
end
alias bdb="brave_default_bookmarks"

function fzf_mark_by_buku
    set website (buku --suggest -p -f 5 | column -ts '  ' | fzf $FZF_CUSTOM_PARAMS \
        --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' \
        --bind 'ctrl-y:execute-silent(buku --nostdin -p {1} | grep -Eo "https?://[^[:space:]]+" | pbcopy)+abort' \
        --preview='buku --nostdin -p {1}' \
        --header="$(_buildFzfHeader '' 'fzf_mark_by_buku')" \
        --multi)
    for i in $website
        set index (echo -n $i | awk '{print $1}')
        buku -p $index
        buku -o $index
    end
end
alias fmb="fzf_mark_by_buku"

function browser_bookmarks_manage
    while true
        set -l action (printf "%s\n" \
            "🔎 Safari" \
            "🔎 Chrome_Default" \
            "🔎 Chrome_Profile1" \
            "🔎 Brave_Default" \
            "🔎 Bubu" \
            "🚪 退出系统" | \
            fzf --header " 浏览器收藏记录管理系统 " \
                --prompt "主菜单 ❯ " \
                --preview-window=up:30% \
                --preview "echo '选择操作类型'" \
                --height=15% \
                --header="$(_buildFzfHeader '' 'browser_bookmarks_manage')" \
                --reverse)

        switch "$action"
            case '*Safari*'
                fzf_safari_bookmarks
            case '*Chrome_Default*'
                chrome_default_bookmarks
            case '*Chrome_Profile1*'
                chrome_profile1_bookmarks
            case '*Brave_Default*'
                brave_default_bookmarks
            case '*Bubu*'
                fzf_mark_by_buku
            case '*退出系统*'
                return
        end
    end
end

alias bm="browser_bookmarks_manage"
bind -M insert µ browser_bookmarks_manage

function goodfon
    set -l DEFAULTBROWSER "/Applications/Firefox.app"      # default browser for open goodfon
    set -l SECONDBROWSER "/Applications/Google Chrome.app" # second browser for open goodfon
    set -l URL "https://www.goodfon.ru/"

    if test -z $argv[1]
        if test -d $DEFAULTBROWSER
            /usr/bin/open -a $DEFAULTBROWSER $URL
        end
    end

    if test "$argv[1]" = "chrome" -o "$argv[1]" = "google"
        if test -d $SECONDBROWSER
            /usr/bin/open -a $SECONDBROWSER $URL
        end
    end
end
alias gfon="goodfon"

function _checkDirFull
    if test -n $argv[1]
        set -l maxsize 2000
        set -l picpath (dirname $argv[1])
        set -l cursize (ls $picpath | wc -l)

        if test $cursize -ge $maxsize
            set -l curcount (echo $picpath | tr -cd "[0-9]")
            set -l tmpmiddlecount $curcount
            set -l curcount (math $curcount + 1)
            if test $curcount -le 9
                set -l curcount 0$curcount
            end
            set -l prefixpath (echo $picpath | sed "s,"$tmpmiddlecount",,g")
            set -l newpath $prefixpath$curcount
            if not test -d $newpath
                mkdir $newpath
            end
            mv $argv[1] $newpath/(basename $argv[1])
            echo "$argv[1] $newpath/(basename $argv[1])"
        end
    end
end