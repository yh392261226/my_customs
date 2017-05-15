#!/bin/bash

show_msg=0 #是否显示当前切换图片地址提示
phpbin=/usr/local/bin/php

##### 背景图变换
if [ "$MYSYSNAME" = "Mac" ]; then #判断是否是os系统
    ITERMPATH="/Applications/iTerm.app"
    if [ -d "$ITERMPATH" ]; then #判断是否安装了iterm
        image_list=( $(/bin/ls $MYPATH/pictures/) )
        image_index=-1
        #图像缩略图
        bg_thumb() {
            bgfile=$1
            if [ ! -f "$bgfile" ]; then
                echo "No bg at the current time!";
                exit 1
            else
                clear
                #printf '\033]1337;File=inline=1;width=30%%;height=10%%;preserveAspectRatio=0'
                printf '\033]1337;File=inline=1;width=20%%;preserveAspectRatio=0'
                printf ":"
                base64 < "$bgfile"
                printf '\a\n'
                echo ""
                echo ""
                return 0
            fi
        }
        #图像切换函数
        function bg_change() {
            image_path=$1
            image_index=$2
            CURITERMVERSION=$(lsappinfo info -only name `lsappinfo front` |awk -F'"LSDisplayName"="' '{print $2}'|cut -d '"' -f 1)
            if [ "" != "$image_index" ]; then
                if [ -f $MYPATH/tools/current_picture ]; then
                    /bin/rm -f $MYPATH/tools/current_picture
                fi
                echo $image_index > $MYPATH/tools/current_picture
            fi
            if [ -f $MYPATH/tools/current_picturename ]; then
                /bin/rm -f $MYPATH/tools/current_picturename
            fi
            echo "$image_path" > $MYPATH/tools/current_picturename

            if [ "$show_msg" = "1" ]; then
                if [ ! -z "$image_path" ]; then
                    terminal-notifier -message $image_path
                fi
            fi

            if [ "$CURITERMVERSION" = "iTerm2" ]; then
                osascript -e "tell application \"iTerm.app\"
                    tell current window
                        tell current session
                            set background image to \"$image_path\"
                        end tell
                    end tell
                end tell"
            else
                osascript -e "tell application \"iTerm\"
                    set current_terminal to (current terminal)
                    tell current_terminal
                        set current_session to (current session)
                        tell current_session
                            set background image path to \"$image_path\"
                        end tell
                    end tell
                end tell"
            fi
            bg_thumb $image_path
        }

        #随机下一个背景图
        function bg_rand_next() {
            if [ -z "$BUFFER" ]; then
                image_path=$($phpbin $MYPATH/tools/pictures.php next);
                bg_change $image_path
            else
                self-insert '"˚"'
            fi
        }

        #随机一个背景图
        function bg_rand() {
            if [ -z "$BUFFER" ]; then
                image_path=$($phpbin $MYPATH/tools/pictures.php rand);
                bg_change $image_path
            else
                self-insert '"∆"'
            fi
        }

        #随机上一个背景图
        function bg_rand_pre() {
            if [ -z "$BUFFER" ]; then
                image_path=$($phpbin $MYPATH/tools/pictures.php pre);
                bg_change $image_path
            else
                self-insert '"˙"'
            fi
        }

        #背景图设置为空
        function bg_empty() {
            if [ -z "$BUFFER" ]; then
                image_path=
                bg_change $image_path
            else
                self-insert '"∫"'
            fi
        }

        bind -x '"˙":"bg_rand_pre"'    #//Alt h 换背景 (随机的上一个)
        bind -x '"∆":"bg_rand"'        #//Alt j 换背景 (随机一个)
        bind -x '"˚":"bg_rand_next"'   #//Alt k 换背景 (随机的下一个)

        bind -x '"∫":"bg_empty"'       #//Alt b 背景换成空的
    fi

#    控制打开终端就自动随机更换一次背景
#     bg_rand
fi
