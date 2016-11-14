#####系统参数
export MYRUNTIME=$(cat ~/.myruntime)
MYPATH=$MYRUNTIME
ZSH=$MYPATH/oh-my-zsh
OHTMPPATH=/tmp/oh-my-zsh
USERNAME=`/usr/bin/whoami`

#####判断系统名称
if [ "$(uname -s|awk '/Darwin/')" ]; then
    MYSYSNAME='Mac'
    SYSHEADER=''
elif [ "$(uname -s|awk '/Linux/')" ]; then
    if [ "$(cat /etc/issue|awk '/Ubuntu/')" ]; then
        MYSYSNAME='Ubuntu'
        SYSHEADER='☢'
    elif [ "$(cat /etc/issue|awk '/CentOS/')" ]; then
        MYSYSNAME='Centos'
        SYSHEADER='۞'
    else
        MYSYSNAME='Unknow'
        SYSHEADER='㊭'
    fi
else
    MYSYSNAME='Unknow'
    SYSHEADER='☭'
fi
