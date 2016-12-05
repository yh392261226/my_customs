#!/usr/local/bin/fish

set show_msg 0 #是否显示当前切换图片地址提示
set phpbin /usr/local/bin/php
set MYSYSNAME Mac
set ITERMPATH "/Applications/iTerm.app"
set image_list (/bin/ls $MYPATH/pictures/)

function bg_change
    set image_path $argv
    if test -f $MYPATH/tools/current_picturename
        rm -f $MYPATH/tools/current_picturename
    end
    echo "$image_path" > $MYPATH/tools/current_picturename

	if test "$show_msg" = "1"
        if test not -z "$image_path"
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
end

#随机下一个背景图
function bg_rand_next
    if test -z "$BUFFER"
        set image_path (/usr/local/bin/php $MYPATH/tools/pictures.php next)
        bg_change $image_path
    end
end

#随机一个背景图
function bg_rand
    if test -z "$BUFFER"
        set image_path (/usr/local/bin/php $MYPATH/tools/pictures.php rand)
        bg_change $image_path
    end
end

#随机上一个背景图
function bg_rand_pre
    if test -z "$BUFFER"
        set image_path (/usr/local/bin/php $MYPATH/tools/pictures.php pre);
        bg_change $image_path
    end
end

#背景图设置为空
function bg_empty
    if test -z "$BUFFER"
        set image_path
        bg_change $image_path
    end
end

if bind -M insert > /dev/null 2>&1
    bind -M insert \cq bg_rand_pre
    bind -M insert \cw bg_rand
    bind -M insert \ce bg_rand_next
    bind -M insert \cb bg_empty
end
