
# Desc: 显示所有含有字符串的自定义命令及注释
function showa () {
    MYRUNTIME=$(cat $HOME/.myruntime)
    customcd $MYRUNTIME/customs/my_shell/library/functions; find *.sh | xargs ag "$1" | awk -F':' '{print $1}' | fzf  --no-sort --tac --toggle-sort=ctrl-r --height 95% --reverse --preview 'cat {}' --preview-window right:140
    # grep --color=always -i -a2 $@ $MYRUNTIME/customs/my_shell/my_alias.sh $MYRUNTIME/customs/my_shell/my_func.sh | grep -v '^\s*$' | less -FSRXc ;
}

# Desc: 显示所有自定义命令及注释
function showaliases() {
    MYRUNTIME=$(cat $HOME/.myruntime)
    #customcd $MYRUNTIME/customs/my_shell/library/functions; ls *.sh| fzf --no-sort --tac --toggle-sort=ctrl-r --height 95% --reverse --preview 'cat {}' --preview-window right:140
    cd $MYRUNTIME/customs/my_shell/library/functions; ls *.sh| fzf --no-sort --tac --toggle-sort=ctrl-r --height 95% --reverse --preview 'cat {}' --preview-window right:140
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

# Desc: 显示从a-z的我的自定义命令
function a2z() {
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

# Desc: 更新iterm2的扩展shell
function upshell() {
	curl -L https://iterm2.com/shell_integration/install_shell_integration_and_utilities.sh | bash
}

# Desc: List processes owned by my user:
function myps() { ps $@ -u $USER -o pid,%cpu,%mem,start,time,bsdtime,command ; }

# Desc: 显示我的自定义SHELL头信息
function myMessage() {
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

# Desc: acd 操作？
function acdul() {
    acdcli ul -x 8 -r 4 -o "$@"
}

# Desc: 列出所有失效软连接
function badlink() {
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

# Desc: 生成【参数为后缀名的】的数据文件
function csbuild() {
    [ $# -eq 0 ] && return

    cmd="find `pwd`"
    for ext in $@; do
        cmd=" $cmd -name '*.$ext' -o"
    done
    echo ${cmd: 0: ${#cmd} - 3}
    eval "${cmd: 0: ${#cmd} - 3}" > cscope.files &&
        cscope -b -q && rm cscope.files
}

# Desc: 清理摄像头缓存
function clearcamera() {
    sudo killall VDCAssistant
}

# Desc: 2019-07-12 TNT破解失效 更改签名
function codesign() {
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

# Desc: Figlet 字体选择器
function fgl() {
    cd /usr/local/Cellar/figlet/*/share/figlet/fonts
    BASE=`pwd`
    figlet -f `ls *.flf | sort | fzf` $*
}

# Desc: 最简化 终端主题
function miniprompt() {
    unset PROMPT_COMMAND
    PS1="\[\e[38;5;168m\]> \[\e[0m\]"
}

# Desc: 利用osx系统发音说话
function speaking() {
    words=$1
    if [ $# -ne 1 ]; then
        echo "请输入要说的话"
        echo "例如：$0 haha "
        return 1
    fi
    #osascript -e 'say "'$words'" using "Cellos"'
    osascript -e 'say "'$words'" using "Ting-Ting"'
}

# Desc: 获取哈尔滨天气
function myweather() {
    /usr/bin/curl http://wttr.in/harbin?lang=zh
}

# Desc: 按执行次数倒序显示历史命令
function history_sort() {
    local last_command_type=`history | tail -n 1 | awk '{print($0~/^[-]?([0-9])+[.]?([0-9])+$/)?"number":"string"}'`
    if [ "$last_command_type" = "number" ]; then
        history | awk '{$1="";print}' | sort -rn | uniq -c | sort -rn | less
    else
        history | sort -rn | uniq -c | sort -rn | less
    fi
}

# Desc: 列出历史操作命令 选择后执行
function fh() {
  eval $( ([ -n "$ZSH_NAME" ] && fc -l 1 || history) | fzf +s --tac | sed 's/ *[0-9]* *//')
}

# Desc: help 帮助 man
function help() {

}