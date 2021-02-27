#!/usr/bin/env fish
set -gx  SOURCED_FISH_CHANGEBG 1
set -gx  show_msg 0 #是否显示当前切换图片地址提示
if test -e /usr/local/bin/php
    set -gx  phpbin /usr/local/bin/php
end
if test -e /opt/homebrew/bin/php
    set -gx  phpbin /opt/homebrew/bin/php
end
set -gx  MYSYSNAME Mac
set -gx  ITERMPATH "/Applications/iTerm.app"
# set -gx  image_list (/bin/ls $MYPATH/pictures/)
set -gx  curappname (env | grep 'TERM_PROGRAM=' | sed 's/TERM_PROGRAM=//')
set -gx  bg_change_can_use 0
if test -e /usr/local/bin/php
    set -gx  bg_change_php_command_bin /usr/local/bin/php
end
if test -e /opt/homebrew/bin/php
    set -gx  bg_change_php_command_bin /opt/homebrew/bin/php
end
set -gx  bg_change_php_code_bin $MYPATH/customs/others/pictures.php
if test -e /usr/local/bin/terminal-notifier
    set -gx  terminal_notifier_bin /usr/local/bin/terminal-notifier
end
if test -e /opt/homebrew/bin/terminal-notifier
    set -gx  bg_change_php_command_bin /opt/homebrew/bin/terminal-notifier
end

#set -gx  osascript_bin /usr/bin/osascript
set -gx  current_picturename {$MYPATH}/tools/current_picturename

if test "$MYSYSNAME" = "Mac"                    #判断是否是os系统
    if test -d $ITERMPATH                       #判断是否安装了iterm
        if test $curappname = "iTerm.app"       #判断当前使用的是否是iterm
          set -gx bg_change_can_use 1
        end
    end
end


#图像缩略图
function bg_thumb
    if test "$bg_change_can_use" != 1
        false
    end
    set bgfile $argv
    if test not -f $bgfile
        echo "No bg at the current time!";
        false
    else
        clear
        printf '\033]1337;File=inline=1;width=20%%;preserveAspectRatio=0'
        printf ":"
        base64 < "$bgfile"
        printf '\a\n'
        echo ""
        echo ""
        true
    end
end

#更换背景图片
function bg_change
    if test "$bg_change_can_use" != 1
        false
    end
    set image_path $argv
    if test -f "$current_picturename"
        rm -f $current_picturename
    end
    echo "$image_path" > $current_picturename

    if test "$show_msg" = "1"
        if test -n "$image_path"
            $terminal_notifier_bin -message $image_path
        end
    end

    osascript -e "tell application \"iTerm.app\"
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
    if test "$bg_change_can_use" != 1
        false
    end
    set image_path (eval $bg_change_php_command_bin $bg_change_php_code_bin next)
    bg_change $image_path
end

#随机一个背景图
function bg_rand
    if test "$bg_change_can_use" != 1
        false
    end
    set image_path (eval $bg_change_php_command_bin $bg_change_php_code_bin rand)
    bg_change $image_path
end

#随机上一个背景图
function bg_rand_pre
    if test "$bg_change_can_use" != 1
        false
    end
    set image_path (eval $bg_change_php_command_bin $bg_change_php_code_bin pre);
    bg_change $image_path
end

#背景图设置为空
function bg_empty
    if test "$bg_change_can_use" != 1
        false
    end
    set image_path
    bg_change $image_path
end

bind -M insert \cq bg_rand_pre
bind -M insert \cw bg_rand
bind -M insert \ce bg_rand_next
bind -M insert \cb bg_empty
