# Desc: cat 打印which命令找到的文件地址
function catw() {
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        cat `which "$1"`
    else
        cat $(type "$1" | awk '{print $NF}')
    fi
}

# Desc: bat 打印which命令找到的文件地址
function batw() {
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        bat `which "$1"`
    else
        bat $(type "$1" | awk '{print $NF}')
    fi
}

# Desc: Opens any file in MacOS Quicklook Preview
function ql () { qlmanage -p "$*" >& /dev/null; }    # ql:           Opens any file in MacOS Quicklook Preview

# Desc:get md5 or sha1 value of the file
function hashfile() {
    local MD5COMMAND=/sbin/md5
    local SHASUMCOMMAND=/usr/local/bin/shasum

    local paras=$?        #参数个数
    local filename=$1     #文件名
    local action=$2       #验证方法

    if [ "" = "$filename" ]; then
        echo "Please type the file name!";
        echo "Example: $0 abc.log ";
        return 1;
    fi


    if [ "$action" = "sha1" ] || [ "$action" = "shasum" ]; then
        $SHASUMCOMMAND $filename | awk '{print $1}' #sha1 file
    else
        $MD5COMMAND $filename | awk -F'=' '{print $2}' #default is md5 file
    fi
}

# Desc: diff the two files md5 value
function check2filesbymd5() {
    local MD5COMMAND=/sbin/md5 #md5 command
    local LOCALPATH=$1 #args[0]
    local TARGETPATH=$2 #args[1]

    if [ ! -f $LOCALPATH ] || [ ! -f $TARGETPATH ]; then # one of the files is not exists
        echo "Please check the args, File or Path is not exists!"; return 1
    fi
    ## Both of the two files are exists, diff them
    if [ "$($MD5COMMAND $LOCALPATH)" = "$($MD5COMMAND $TARGETPATH)" ]; then
        #echo "The same file !";
        RESULT="The same file !";
    else
        #echo $LOCALPATH "and" $TARGETPATH ", are the diffrent files !";
        RESULT=$LOCALPATH "and" $TARGETPATH ", are the diffrent files !";
    fi
    echo $RESULT
    return 0
}

# Desc: 变更权限rwx为权限值【777】
function mla() {
    ls -l  "$@" | awk '
        {
        k=0;
        for (i=0;i<=8;i++)
            k+=((substr($1,i+2,1)~/[rwx]/) *2^(8-i));
        if (k)
            printf("%0o ",k);
        printf(" %9s  %3s %2s %5s  %6s  %s %s %s\n", $3, $6, $7, $8, $5, $9,$10, $11);
        }'
}

