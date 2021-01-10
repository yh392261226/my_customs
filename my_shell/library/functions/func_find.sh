# Desc:寻找当前目录下后缀名的所有文件
function lsext() {
    find . -type f -iname '*.'${1}'' -exec ls -l {} \; ;
}

# Desc: Find file whose name ends with a given string
function ffe () { /usr/bin/find . -name '*'"$@" ; }

# Desc: Find file whose name starts with a given string
function ffs () { find . -name "$@"'*' ; }

# Desc: 查找当前目录中包含某个字符串的
function mqfind () {
    find . -exec grep -l -s $1 {} \;
    return 0
}

# Desc: Find file under the current directory
function ff () { find . -name "$@" ; }

#   findPid: find out the pid of a specified process
#   -----------------------------------------------------
#       Note that the command name can be specified via a regex
#       E.g. findPid '/d$/' finds pids of all processes with names ending in 'd'
#       Without the 'sudo' it will only find processes of the current user
#   -----------------------------------------------------

# Desc: find out the pid of a specified process
function findPid () { lsof -t -c "$@" ; }

# Desc: find files which has the same md5 value
function findmd5same() {
    local MD5COMMAND=/sbin/md5
    local SOURCEPATH=$1
    local TMPFILE=/tmp/findmd5same_tmp
    local TMPKEYSFILE=/tmp/findmd5same_keys_tmp
    local RESULTFILE=$HOME/Desktop/samemd5file_result

    source $MYRUNTIME/customs/bin/mymessage
    if [ ! -d $SOURCEPATH ]; then
        echo "The path $SOURCEPATH does not exists!";
        exit 1
    fi

    if [ -f $TMPFILE ] || [ -f $TMPKEYSFILE ]; then
        /bin/rm -f $TMPFILE $TMPKEYSFILE
    fi

    for i in $(ls $SOURCEPATH); do
        echo $($MD5COMMAND $SOURCEPATH/$i | awk -F'=' '{print $2}') $SOURCEPATH/$i >> $TMPFILE
    done

    if [ -f $TMPFILE ]; then
        cat $TMPFILE | awk '{print $1}' | sort -rn |uniq -c | awk '$1 > 1 {print $2}' >> $TMPKEYSFILE
    fi

    if [ -f $TMPKEYSFILE ]; then
        for ii in $(cat $TMPKEYSFILE); do
            if [ "" != "$ii" ]; then
                cat $TMPFILE | grep $ii | awk '{print $2}' >> $RESULTFILE
            fi
        done
    fi

    rm -f $TMPKEYSFILE $TMPFILE
    if [ -f $RESULTFILE ]; then
        echo "Please check the result data, " $RESULTFILE
        exit 0
    fi
}

# Desc: fkill - kill processes - list only the ones you can kill. Modified the earlier script.
function fkill() {
    local pid
    if [ "$UID" != "0" ]; then
        pid=$(ps -f -u $UID | sed 1d | fzf -m | awk '{print $2}')
    else
        pid=$(ps -ef | sed 1d | fzf -m | awk '{print $2}')
    fi

    if [ "x$pid" != "x" ]
    then
        echo $pid | xargs kill -${1:-9}
    fi
}

# Desc: Search for a file using MacOS Spotlight's metadata
function spotlight () { mdfind "kMDItemDisplayName == '$@'wc"; }

