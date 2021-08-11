function show_aliases() { # Desc: show_aliases:显示所有含有字符串的自定义命令及注释
    if [ ""  != "$1" ]; then
        MYRUNTIME=$(cat $HOME/.myruntime)
        customcd $MYRUNTIME/customs/my_shell/library/functions; find *.sh | xargs ag "$1" | awk -F':' '{print $1}' | sort | uniq | fzf  --no-sort --tac --toggle-sort=ctrl-r --height 95% --reverse --preview 'bat {}' --preview-window right:140
        # grep --color=always -i -a2 $@ $MYRUNTIME/customs/my_shell/my_alias.sh $MYRUNTIME/customs/my_shell/my_func.sh | grep -v '^\s*$' | less -FSRXc ;
    else
        echo "Usage:$0 condition"
    fi
}
alias showa="show_aliases"

function fzf_show_functions() { # Desc: fzf_show_functions:显示所有自定义命令及注释
    find $MYRUNTIME/customs/my_shell/library/functions/ -type f -name "*sh" |xargs grep 'function .*().*Desc' |sed 's/Desc:/Î/' |awk -F'Î' '{print $2}' |fzf  --no-sort --tac --toggle-sort=ctrl-r --height 95% --reverse --preview "bash $MYRUNTIME/customs/bin/check_custom_functions {}" --preview-window right:140
}
alias showfuncs="fzf_show_functions"

function fzf_show_aliases2() { # Desc: fzf_show_aliases2:显示所有自定义命令及注释
    MYRUNTIME=$(cat $HOME/.myruntime)
    #customcd $MYRUNTIME/customs/my_shell/library/functions; ls *.sh| fzf --no-sort --tac --toggle-sort=ctrl-r --height 95% --reverse --preview 'cat {}' --preview-window right:140
    ls $MYRUNTIME/customs/my_shell/library/functions/*.sh| fzf --no-sort --tac --toggle-sort=ctrl-r --height 95% --reverse --preview 'cat {}' --preview-window right:140
    # touch /tmp/tmp_all_aliases.log
    # for file in $(ls $MYRUNTIME/customs/my_shell/library/functions/*.sh); do
    #     cat $file | grep '^function ' | awk '{print "Command: " $2}' | sed 's/()//' | sed 's/{//' >> /tmp/tmp_all_aliases.log
    #     cat $file | grep 'Desc:' | sed 's/#//' | sed 's/[ ][ ]*//' >> /tmp/tmp_all_aliases.log
    #     echo '---------------------------------------------------' >> /tmp/tmp_all_aliases.log
    # done
    # if [ -f /tmp/tmp_all_aliases.log ]; then
    #     cat /tmp/tmp_all_aliases.log | fzf --no-sort --tac --toggle-sort=ctrl-r --height 40% --reverse --preview 'cat {}' --preview-window right:140
    #     # rm -f /tmp/tmp_all_aliases.log
    # fi
}
alias showaliases="fzf_show_aliases2"

function show_aliases_from_a2z() { # Desc: show_aliases_from_a2z:显示从a-z的我的自定义命令
    echo "********************************************************"
    echo "*** Already exists command:"
    echo "********************************************************"
    for word in {a..z}; do
        if [ "$(command -v $word)" != "" ]; then
            type $word | grep -v 'not found';
            if [ "$nowshell" != "bash" ]; then
                echo "________________________________________________________"
                which $word | grep -v 'not found';
            fi
            echo "________________________________________________________"
            echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
        fi
    done
}
alias a2z="show_aliases_from_a2z"

function update_shell() { # Desc: update_shell:更新iterm2的扩展shell
	curl -L https://iterm2.com/shell_integration/install_shell_integration_and_utilities.sh | bash
}
alias upshell="update_shell"

function my_ps() { # Desc: my_ps:List processes owned by my user:
    ps $@ -u $USER -o pid,%cpu,%mem,start,time,bsdtime,command ;
}
alias myps="my_ps"

function my_message() { # Desc: my_message:显示我的自定义SHELL头信息
    clear
    _COLUMNS=$(tput cols)
    source $MYRUNTIME/tools/m_title
    y=$(( ( $_COLUMNS - ${#_TITLE} )  / 2 ))
    spaces=$(printf "%-${y}s" " ")
    echo " "
    echo -e "${spaces}\033[41;37;5m ${_TITLE} \033[0m"
    echo " "


    _COLUMNS=$(tput cols)
    source $MYRUNTIME/tools/m_message
    y=$(( ( $_COLUMNS - ${#_MESSAGE} )  / 2 ))
    spaces=$(printf "%-${y}s" " ")
    echo -e "${spaces}${_MESSAGE}"
    echo " "
    for ((i=1; i<=$(tput cols); i ++))  ; do echo -n '*';done

    echo " "
}
alias myMessage="my_message"

function acdul() { # Desc: acdul:acd 操作？
    acdcli ul -x 8 -r 4 -o "$@"
}

function show_bad_links() { # Desc: show_bad_links:列出所有失效软连接 默认读取家目录 可以指定目录badlink /data
    local readpath=$HOME
    if [ "" != "$1" ]; then
        readpath=$1
    fi
    echo "File List broken links:"
    for file in $(ls -a $readpath); do
    realpath=$(/usr/bin/readlink $readpath/$file)
    if [ ! -f $realpath ] && [ ! -d $realpath ]; then
        echo $readpath/$file
    fi
    done
}
alias badlink="show_bad_links"

function csbuild() { # Desc: csbuild:生成【参数为后缀名的】的数据文件
    [ $# -eq 0 ] && return

    cmd="find `pwd`"
    for ext in $@; do
        cmd=" $cmd -name '*.$ext' -o"
    done
    echo ${cmd: 0: ${#cmd} - 3}
    eval "${cmd: 0: ${#cmd} - 3}" > cscope.files &&
        cscope -b -q && rm cscope.files
}

function clear_camera() { # Desc: clear_camera:清理摄像头缓存
    sudo killall VDCAssistant
}

function codesign() { # Desc: codesign:2019-07-12 TNT破解失效 更改签名
    if [ $# -ne 1 ]; then
        echo "Type $0 App path to replace the app sign"
        return 1
    fi
    if [ -d "$1" ]; then
        codesign --force --deep --sign - "$1"
    else
        echo "The app path does not exists !!!"
        return 1
    fi
}

function fzf_figlet_font_selector() { # Desc: fzf_figlet_font_selector:Figlet 字体选择器
    cd $(brew --prefix)/figlet/*/share/figlet/fonts
    BASE=`pwd`
    figlet -f `ls *.flf | sort | fzf` $*
}
alias fgl="fzf_figlet_font_selector"

function miniprompt() { # Desc: miniprompt:临时最简化 终端主题
    unset PROMPT_COMMAND
    PS1="\[\e[38;5;168m\]> \[\e[0m\]"
}

function speaking() { # Desc: speaking:利用osx系统发音说话
    words=$1
    if [ $# -ne 1 ]; then
        echo "请输入要说的话"
        echo "例如：$0 haha "
        return 1
    fi
    #osascript -e 'say "'$words'" using "Cellos"'
    osascript -e 'say "'$words'" using "Ting-Ting"'
}

function my_weather() { # Desc: my_weather:获取哈尔滨天气
    if [ -f /opt/homebrew/opt/curl/bin/curl ]; then
        /opt/homebrew/opt/curl/bin/curl https://wttr.in/harbin\?lang\=zh
        return
    fi
    curl https://wttr.in/harbin\?lang\=zh
}
alias myewather="my_weather"

function history_sort() { # Desc: history_sort:按执行次数倒序显示历史命令
    local last_command_type=`history | tail -n 1 | awk '{print($0~/^[-]?([0-9])+[.]?([0-9])+$/)?"number":"string"}'`
    if [ "$last_command_type" = "number" ]; then
        history | awk '{$1="";print}' | sort -rn | uniq -c | sort -rn | less
    else
        history | sort -rn | uniq -c | sort -rn | less
    fi
}

function fzf_history_select() { # Desc: fzf_history_select:列出历史操作命令 选择后执行
    eval $( ([ -n "$ZSH_NAME" ] && fc -l 1 || history) | fzf +s --tac | sed 's/ *[0-9]* *//')
}
alias fh="fzf_history_select"

function help_by_tldr() { # Desc: help_by_tldr:help 帮助 tldr命令别名
    tldr $@
}
alias help="help_by_tldr"

function p() { # Desc: p:ps -ef |grep 进程
    ps -ef|grep "$@" | grep -v grep |fzf
}

if [ -f /usr/local/bin/bashtop ]; then
    function btop() { # Desc: btop:bashtop命令的别名 
        /usr/local/bin/bashtop "$@"
    }
fi

if [ -f /usr/local/bin/shellcheck ]; then
    function shell_debug() { # Desc:shell_debug:依赖shellcheck对shell脚本debug
        /usr/local/bin/shellcheck "$@"
    }
fi

if command -v COMMAND &> /dev/null; then
    function fzf_history() { # Desc:fzf_history:依赖fzf 读取history结果
        history | fzf
    }
    alias fhistory="fzf_history"
fi

function file_tree() { # Desc:filetree:tree命令
	path='./'
	[[ "" != "$1" ]] && path=$1
	ls -R $path | grep ":$" | sed -e 's/:$//' -e 's/[^-][^\/]*\//--/g' -e 's/^/ /' -e 's/-/|/'
}
alias filetree="file_tree"
