set MYRUNTIME (cat $HOME/.myruntime)
set MYPATH $MYRUNTIME
set ZSH $MYPATH/oh-my-zsh
set OHTMPPATH /tmp/oh-my-zsh
set USERNAME (/usr/bin/whoami)

if test (uname -s | awk '/Darwin/')
    set MYSYSNAME 'Mac'
    set SYSHEADER ''
    set -x OS_ICON ""
else if test (uname -s | awk '/Linux/')
    if test (cat /etc/issue | awk '/Ubuntu/')
        set MYSYSNAME 'Ubuntu'
        set SYSHEADER '☢'
        set -x OS_ICON "☢"
    else if test (cat /etc/issue | awk '/CentOS/')
        set MYSYSNAME 'Centos'
        set SYSHEADER '۞'
        set -x OS_ICON "۞"
    else
        set MYSYSNAME 'Mac'
        set SYSHEADER '㊭'
        set -x OS_ICON "㊭"
    end
else
    set MYSYSNAME 'Mac'
    set SYSHEADER '☭'
    set -x OS_ICON "☭"
end

set curcpucore (uname -a | awk '{print $NF}')
if test "$curcpucore" = "arm64"
    set -x CPUCORE "arm64"
else if test "$curcpucore" = "x86_64"
    set -x CPUCORE "intel64"
else if test "$curcpucore" = "GNU/Linux"
    if test (uname -a | awk '{ print $(NF-1) }') = "x86_64"
        set -x CPUCORE "linux64"
    else
        set -x CPUCORE "linux"
    end
end
