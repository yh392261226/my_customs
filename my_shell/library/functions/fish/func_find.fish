### Package Desc: 查找相关命令

function find_files_by_ext
    # Desc: function: find_files_by_ext:寻找当前目录下后缀名的所有文件
    if test -n "$argv[1]"
        find ./ -type f -iname "*.$argv[1]" -exec ls -l {} \;
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text")
        else
            read text
        end
        find ./ -type f -iname "*.$text" -exec ls -l {} \;
    end
end
alias fext="find_files_by_ext"

function find_file_by_end
    # Desc: function: find_file_by_end:Find file whose name ends with a given string
    if test -n "$argv"
        /usr/bin/find (pwd) -name "*$argv"
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text")
        else
            read text
        end
        /usr/bin/find (pwd) -name "*$text"
    end
end
alias fend="find_file_by_end"

function find_files_by_start
    # Desc: function: find_fs:Find file whose name starts with a given string
    if test -n "$argv"
        find (pwd) -name "$argv*"
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text")
        else
            read text
        end
        find (pwd) -name "$text*"
    end
end
alias fstart="find_files_by_start"

function find_files_by_contain
    # Desc: function: find_files_by_contain:查找当前目录中包含某个字符串的
    if test -n "$argv[1]"
        find (pwd) -exec grep -l -s $argv[1] {} \;
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text")
        else
            read text
        end
        find (pwd) -exec grep -l -s $text {} \;
    end
    return 0
end
alias fcontain="find_files_by_contain"

function find_file_by_params
    # Desc: function: find_file_by_params:Find file under the current directory
    if test -n "$argv"
        find ./ -name "$argv"
    else
        if test (ifHasCommand gum) = "1"
            set text (gum input --placeholder "Type search text")
        else
            read text
        end
        find ./ -name "$text"
    end
end
alias fparams="find_file_by_params"

function find_same_file_by_md5
    # Desc: function: find_same_file_by_md5:Find files which has the same md5 value
    set MD5COMMAND /sbin/md5
    set SOURCEPATH $argv[1]
    set TMPFILE /tmp/findmd5same_tmp
    set TMPKEYSFILE /tmp/findmd5same_keys_tmp
    set RESULTFILE $HOME/Desktop/samemd5file_result

    source $MYRUNTIME/customs/bin/mymessage
    if not test -d $SOURCEPATH
        echo "The path $SOURCEPATH does not exists!"
        exit 1
    end

    if test -f $TMPFILE; or test -f $TMPKEYSFILE
        /bin/rm -f $TMPFILE $TMPKEYSFILE
    end

    for i in (ls $SOURCEPATH)
        echo ($MD5COMMAND $SOURCEPATH/$i | awk -F'=' '{print $2}') $SOURCEPATH/$i >> $TMPFILE
    end

    if test -f $TMPFILE
        cat $TMPFILE | awk '{print $1}' | sort -rn | uniq -c | awk '$1 > 1 {print $2}' >> $TMPKEYSFILE
    end

    if test -f $TMPKEYSFILE
        for ii in (cat $TMPKEYSFILE)
            if test -n "$ii"
                cat $TMPFILE | grep $ii | awk '{print $2}' >> $RESULTFILE
            end
        end
    end

    rm -f $TMPKEYSFILE $TMPFILE
    if test -f $RESULTFILE
        echo "Please check the result data, " $RESULTFILE
        exit 0
    end
end
alias fmd5="find_same_file_by_md5"
