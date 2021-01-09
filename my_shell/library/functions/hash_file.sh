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