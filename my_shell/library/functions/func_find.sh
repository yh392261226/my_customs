function find_ext() { # Desc: find_ext:寻找当前目录下后缀名的所有文件
    find . -type f -iname '*.'${1}'' -exec ls -l {} \; ;
}

function fext() { # Desc: fext:寻找当前目录下后缀名的所有文件
    find_ext $@
}

function find_fe () { # Desc: find_fe:Find file whose name ends with a given string
    /usr/bin/find . -name '*'"$@" ;
}

function ffe() { # Desc: ffe:Find file whose name ends with a given string
    find_fe $@
}

function find_fs () { # Desc: find_fs:Find file whose name starts with a given string
    find . -name "$@"'*' ;
}

function ffs () { # Desc: ffs:Find file whose name starts with a given string
    find_fs $@
}

function find_mq () { # Desc: find_mq:查找当前目录中包含某个字符串的
    find . -exec grep -l -s $1 {} \;
    return 0
}

function fmq() { # Desc: fmq:查找当前目录中包含某个字符串的
    find_mq $@
}

function find_f () { # Desc: find_f:Find file under the current directory
    find . -name "$@" ;
}

function ff () { # Desc: ff:Find file under the current directory
    find_f $@
}

function find_samemd5() { # Desc: find_samemd5:find files which has the same md5 value
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

function spotlight() { # Desc: spotlight:Search for a file using MacOS Spotlight's metadata
    mdfind "kMDItemDisplayName == '$@'wc";
}

