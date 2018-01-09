show_msg=0 #是否显示当前切换图片地址提示
phpbin=/usr/local/bin/php

##### 背景图变换
if [ "$MYSYSNAME" = "Mac" ]; then #判断是否是os系统
    ITERMPATH="/Applications/iTerm.app"
    if [ -d "$ITERMPATH" ]; then #判断是否安装了iterm
        if [ "$(env | grep 'TERM_PROGRAM=' | sed 's/TERM_PROGRAM=//')" = "iTerm.app" ]; then #判断当前使用的是否是iterm
            image_list=($(/bin/ls $MYPATH/pictures/))
            image_index=-1
            #图像缩略图
            bg_thumb() {
                bgfile=$1
                if [ ! -f "$bgfile" ] && [ "" != "$bgfile" ]; then
                    echo "No bg at the current time!";
                    return 1
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
            bg_change() {
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
                    rm -f $MYPATH/tools/current_picturename
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
                if [ "" != "$image_path" ]; then
                  bg_thumb $image_path
                  for ((i=1; i<=((${#image_path} + 2)); i ++))  ; do echo -n '^';done
                  echo ""
                  echo $image_path
                  echo ""
                  for ((i=1; i<=((${#image_path} + 2)); i ++))  ; do echo -n '^';done
                  echo ""
                fi
            }

            #下一个背景图
            bg_next() {
                if [ -z "$BUFFER" ]; then
                    if test $image_index -ge ${#image_list[*]}; then
                        image_index=-1
                    else
                        image_index=$(( $image_index + 1 ))
                    fi
                    image_path=$image_list[$image_index]
                    bg_change $MYPATH/pictures/$image_path $image_index
                else
                    zle self-insert '^}'
                fi
            }
            zle -N bg_next
            bindkey '^}' bg_next   #//Ctrl }符换背景 (下一个)

            #随机下一个背景图
            bg_rand_next() {
                if [ -z "$BUFFER" ]; then
                    image_path=$($phpbin $MYPATH/tools/pictures.php next);
                    bg_change $image_path
                else
                    zle self-insert '^E'
                fi
            }
            zle -N bg_rand_next
            bindkey '^E' bg_rand_next   #//Ctrl E 换背景 (随机的下一个)

            #随机一个背景图
            bg_rand() {
                if [ -z "$BUFFER" ]; then
                    image_path=$($phpbin $MYPATH/tools/pictures.php rand);
                    bg_change $image_path
                else
                    zle self-insert '^W'
                fi
            }
            zle -N bg_rand
            bindkey '^W' bg_rand   #//Ctrl W 换背景 (随机一个)

            #随机上一个背景图
            bg_rand_pre() {
                if [ -z "$BUFFER" ]; then
                    image_path=$($phpbin $MYPATH/tools/pictures.php pre);
                    bg_change $image_path
                else
                    zle self-insert '^Q'
                fi
            }
            zle -N bg_rand_pre
            bindkey '^Q' bg_rand_pre   #//Ctrl Q 换背景 (随机的上一个)

            #上一个背景图
            bg_pre() {
                if [ -z "$BUFFER" ]; then
                    if test $image_index -le 0; then
                        image_index=${#image_list[*]}
                    else
                        image_index=$(( $image_index - 1 ))
                    fi
                    image_path=$image_list[$image_index]
                    bg_change $MYPATH/pictures/$image_path $image_index
                else
                    zle self-insert '^{'
                fi
            }
            zle -N bg_pre
            bindkey '^{' bg_pre   #//Ctrl {符换背景(上一个)

            #背景图设置为空
            bg_empty() {
                if [ -z "$BUFFER" ]; then
                    bg_change ""
                else
                    zle self-insert '^B'
                fi
            }
            zle -N bg_empty
            bindkey '^B' bg_empty #//Ctrl B 背景换成空的
        fi
    fi

#    控制打开终端就自动随机更换一次背景
#     bg_rand
fi
