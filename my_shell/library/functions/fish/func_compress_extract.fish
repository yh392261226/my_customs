function customExtract
    # Desc: function: customExtract:自动检测文件后缀并自动解压
    if test -z $argv[1]
        echo "Usage: extra <path/file_name>.<zip|rar|bz2|gz|tar|tbz2|tgz|Z|7z|xz|ex|tar.bz2|tar.gz|tar.xz>"
    else
        if test -f $argv[1]
            switch $argv[1]
                case '*.tar.bz2'
                    tar xvjf $argv[1]
                case '*.tar.gz'
                    tar xvzf $argv[1]
                case '*.tar.xz'
                    tar xvJf $argv[1]
                case '*.lzma'
                    unlzma $argv[1]
                case '*.bz2'
                    bunzip2 $argv[1]
                case '*.rar'
                    unrar x -ad $argv[1]
                case '*.gz'
                    gunzip $argv[1]
                case '*.tar'
                    tar xvf $argv[1]
                case '*.tbz2'
                    tar xvjf $argv[1]
                case '*.tgz'
                    tar xvzf $argv[1]
                case '*.zip'
                    unzip $argv[1]
                case '*.Z'
                    uncompress $argv[1]
                case '*.7z'
                    7z x $argv[1]
                case '*.xz'
                    unxz $argv[1]
                case '*.exe'
                    cabextract $argv[1]
                case '*'
                    echo "extract: '$argv[1]' - unknown archive method"
            end
        else
            echo "$argv[1] - file does not exist"
        end
    end
end

alias extra customExtract # Desc: alias: extra: customExtract命令的别名,自动检测文件后缀并自动解压

function archiving_file
    # Desc: function: archiving_file: 压缩解压文件
    switch $argv[1]
        case 'e'
            switch $argv[2]
                case '*.tar.bz2'
                    tar xvjf $argv[2]
                case '*.tar.gz'
                    tar xvzf $argv[2]
                case '*.bz2'
                    bunzip2 $argv[2]
                case '*.rar'
                    unrar x $argv[2]
                case '*.gz'
                    gunzip $argv[2]
                case '*.tar'
                    tar xvf $argv[2]
                case '*.tbz2'
                    tar xvjf $argv[2]
                case '*.tgz'
                    tar xvzf $argv[2]
                case '*.zip'
                    unzip $argv[2]
                case '*.Z'
                    uncompress $argv[2]
                case '*.7z'
                    7z x $argv[2]
                case '*'
                    echo "'$argv[2]' kann nicht mit >ark< entpackt werden"
            end
        case 'c'
            switch $argv[2]
                case '*.tar.*'
                    set arch $argv[2]
                    set files $argv[3..-1]
                    tar cvf (dirname $arch)/($arch:r) $files
                    switch $arch
                        case '*.gz'
                            gzip -9r (dirname $arch)/($arch:r)
                        case '*.bz2'
                            bzip2 -9zv (dirname $arch)/($arch:r)
                    end
                case '*.rar'
                    set files $argv[3..-1]
                    rar a -m5 -r $files
                    rar k $argv[3]
                case '*.zip'
                    set files $argv[3..-1]
                    zip -9r $files
                case '*.7z'
                    set files $argv[3..-1]
                    7z a -mx9 $files
                case '*'
                    echo "Kein gültiger Archivtyp"
            end
        case '*'
            echo "Usage: ark <e(解压)|c(压缩)> <path/file_name>.<zip|rar|bz2|gz|tar|tbz2|tgz|Z|7z|xz|ex|tar.bz2|tar.gz|tar.xz>"
    end
end

alias af archiving_file # Desc: alias: af: archiving_file命令的别名,压缩解压文件

function abs_path
    # Desc: function: abs_path:忘记具体干什么的了
    if test -d $argv[1]
        echo (cd $argv[1]; pwd)
    else if test -f $argv[1]
        if string match -q '*/' $argv[1]
            echo (cd (dirname $argv[1]); pwd)/(basename $argv[1])
        else
            echo (pwd)/$argv[1]
        end
    end
end

alias apath abs_path # Desc: alias: apath:abs_path命令的别名,忘记具体干什么的了

function show_free
    # Desc: function: show_free:释放内存？
    set FREE_BLOCKS (vm_stat | grep free | awk '{ print $3 }' | sed 's/\.//')
    set INACTIVE_BLOCKS (vm_stat | grep inactive | awk '{ print $3 }' | sed 's/\.//')
    set SPECULATIVE_BLOCKS (vm_stat | grep speculative | awk '{ print $3 }' | sed 's/\.//')
    set FREE (math "($FREE_BLOCKS + $SPECULATIVE_BLOCKS) * 4096 / 1048576")
    set INACTIVE ($INACTIVE_BLOCKS * 4096 / 1048576)
    set TOTAL (math "$FREE + $INACTIVE")
    echo "Free:       $FREE MB"
    echo "Inactive:   $INACTIVE MB"
    echo "Total free: $TOTAL MB"
end

alias sfree show_free # Desc: alias: sfree:show_free命令的别名,释放内存？

function compress_zip_file
    # Desc: function: compress_zip_file:压缩目录为zip文件
    zip -r "$argv[1]".zip "$argv[1"]
end

alias czf compress_zip_file # Desc: alias: czf:compress_zip_file命令的别名,压缩目录为zip文件

function compress_git_to_zip
    # Desc: function: compress_git_to_zip:git压缩HEAD版本为zip包
    git archive -o (basename $PWD).zip HEAD
end

alias cg2z compress_git_to_zip # Desc: alias: cg2z:compress_git_to_zip命令的别名,git压
