function lsext() { # Desc: lsext:寻找当前目录下后缀名的所有文件
    find . -type f -iname '*.'${1}'' -exec ls -l {} \; ;
}

function ffe () { # Desc: ffe:Find file whose name ends with a given string
    /usr/bin/find . -name '*'"$@" ;
}

function ffs () { # Desc: ffs:Find file whose name starts with a given string
    find . -name "$@"'*' ;
}

function mqfind () { # Desc: mqfind:查找当前目录中包含某个字符串的
    find . -exec grep -l -s $1 {} \;
    return 0
}

function ff () { # Desc: ff:Find file under the current directory
    find . -name "$@" ;
}

#   findPid: find out the pid of a specified process
#   -----------------------------------------------------
#       Note that the command name can be specified via a regex
#       E.g. findPid '/d$/' finds pids of all processes with names ending in 'd'
#       Without the 'sudo' it will only find processes of the current user
#   -----------------------------------------------------

function findPid () { # Desc: findPid:find out the pid of a specified process
    lsof -t -c "$@" ;
}

function findmd5same() { # Desc: findmd5same:find files which has the same md5 value
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

function fkill() { # Desc: fkill: kill processes - list only the ones you can kill. Modified the earlier script.
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

function spotlight() { # Desc: spotlight:Search for a file using MacOS Spotlight's metadata
    mdfind "kMDItemDisplayName == '$@'wc";
}

