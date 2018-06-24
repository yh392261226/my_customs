#!/usr/local/bin/fish
set SOURCED_FISH_CHANGEBG 1
set show_msg 0 #是否显示当前切换图片地址提示
set phpbin /usr/local/bin/php
set MYSYSNAME Mac
set ITERMPATH "/Applications/iTerm.app"
set PICTURES_PATH {$MYPATH}/pictures/
set image_list (/bin/ls $PICTURES_PATH)
set curappname (env | grep 'TERM_PROGRAM=' | sed 's/TERM_PROGRAM=//')
set emptybackground {$HOME}/Pictures/down_pics/public/t1l-logo-white-shitty.jpg
set CURRENT_PICTURE_MARK {$MYPATH}/tools/current_picture
set CURRENT_PICTURENAME_MARK {$MYPATH}/tools/current_picturename
set PHP_TOOL {$MYPATH}/customs/others/pictures.php

if test "$MYSYSNAME" = "Mac"                    #判断是否是os系统
    if test -d {$ITERMPATH}                     #判断是否安装了iterm
        if test "$curappname" = "iTerm.app"     #判断当前使用的是否是iterm
            #图像缩略图
            function bg_thumb
                set bgfile $argv
                if test not -f {$bgfile}
                    echo "No bg at the current time!";
                    false
                else
                    clear
                    #printf '\033]1337;File=inline=1;width=30%%;height=10%%;preserveAspectRatio=0'
                    printf '\033]1337;File=inline=1;width=20%%;preserveAspectRatio=0'
                    printf ":"
                    base64 < "$bgfile"
                    printf '\a\n'
                    echo ""
                    echo ""
                    true
                end
            end

            function bg_change
                set image_path $argv
                if test -f {$CURRENT_PICTURENAME_MARK}
                    rm -f {$CURRENT_PICTURENAME_MARK}
                end
                echo "$image_path" > {$CURRENT_PICTURENAME_MARK}

                if test "$show_msg" = "1"
                    if test -n "$image_path"
                      /usr/local/bin/terminal-notifier -message $image_path
                    end
                end

                /usr/bin/osascript -e "tell application \"iTerm.app\"
                    tell current window
                        tell current session
                            set background image to \"$image_path\"
                        end tell
                    end tell
                end tell"
                if test "$BGTHUMB" = 1
                  bg_thumb $image_path
                end

            end

            #随机下一个背景图
            function bg_rand_next
                if test -z "$BUFFER"
                    set image_path ({$phpbin} {$PHP_TOOL} next)
                    bg_change $image_path
                end
            end

            #随机一个背景图
            function bg_rand
                if test -z "$BUFFER"
                    set image_path ({$phpbin} {$PHP_TOOL} rand)
                    bg_change $image_path
                end
            end

            #随机上一个背景图
            function bg_rand_pre
                if test -z "$BUFFER"
                    set image_path ({$phpbin} {$PHP_TOOL} pre);
                    bg_change $image_path
                end
            end

            #背景图设置为空
            function bg_empty
                if test -z "$BUFFER"
                    set image_path {$emptybackground}
                    bg_change $image_path
                end
            end

            if bind -M insert > /dev/null 2>&1
                bind -M insert \cq bg_rand_pre
                bind -M insert \cw bg_rand
                bind -M insert \ce bg_rand_next
                bind -M insert \cb bg_empty
            end
        end
    end
end
