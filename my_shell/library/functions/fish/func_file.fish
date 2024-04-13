function cat_whereis_file
    if not test (ifHasCommand $argv) = "1"
        echo "Command $argv does not exists !"
        return 1
    end

    if test -n (type "$argv[1]" | grep 'a function with definition'); and test -n (type "$argv[1]" | grep 'a alias')
        cat (which "$argv[1]")
    else
        set endfile (type "$argv[1]" | awk '{print $NF}')
        if test -f $endfile
            cat $endfile
        else
            cat_whereis_file $endfile
        end
    end
end
alias catw="cat_whereis_file"

function bat_whereis_file
    if not test (ifHasCommand gum) = "1"
        echo "Command $argv does not exists !"
        return 1
    end

    if test -n (type "$argv[1]" | grep 'a function with definition'); and test -n (type "$argv[1]" | grep 'a alias')
        bat (which "$argv[1]")
    else
        set endfile (type "$argv[1]" | awk '{print $NF}')
        if test -f $endfile
            bat $endfile
        else
            bat_whereis_file $endfile
        end
    end
end
alias batw="bat_whereis_file"

function quick_preview
    qlmanage -p $argv >& /dev/null
end
alias ql="quick_preview"

function get_hash_file
    set MD5COMMAND /sbin/md5
    set SHASUMCOMMAND /usr/local/bin/shasum

    set paras (count $argv)        #参数个数
    set filename $argv[1]     #文件名
    set action $argv[2]       #验证方法

    if [ "" = "$filename" ]
        echo "Please type the file name!"
        echo "Example: $argv[0] abc.log "
        return 1
    end

    if [ "$action" = "sha1" ] -o [ "$action" = "shasum" ]
        $SHASUMCOMMAND $filename | awk '{print $1}' #sha1 file
    else
        $MD5COMMAND $filename | awk -F'=' '{print $2}' #default
    end
end
alias hashf="get_hash_file"

function fzf_file_to_preview
    set nums (count $argv)
    if test $nums -lt 1
        set nums 500
    end
    fzf $FZF_CUSTOM_PARAMS \
        --preview-window right:70%:rounded:hidden:wrap \
        --header="$(_buildFzfHeader '' 'fzf_file_to_preview')" \
        --preview '[[ (file --mime {}) =~ binary ]] && echo {} is a binary file || (bat --style=numbers --color=always {} || rougify {} || highlight -O ansi -l {} || coderay {} || cat {}) 2> /dev/null | head -n 500'
end
alias fttp="fzf_file_to_preview"

function fzf_open_or_edit
    set -l IFS \n
    set out (fzf $FZF_CUSTOM_PARAMS \
            --preview-window right:70%:rounded:hidden:wrap \
            --preview 'bat {}' \
            --query $argv[1] \
            --exit-0 \
            --expect=ctrl-o,ctrl-e \
            --header=(_buildFzfHeader '' 'fzf_open_or_edit') \
        )
    set key (echo $out | head -n 1)
    set file (echo $out | head -n 2 | tail -n 1)
    if test -n $file
        if test $key = "ctrl-o"
            open $file
        else
            if not set -q EDITOR
                set -x EDITOR vim
            end
            $EDITOR $file
        end
    end

end
alias foe="fzf_open_or_edit"

function fzf_search_term
    if not test (count $argv) -gt 0
        echo "Need a string to search for!"
        return 1
    end
    rg --files-with-matches --no-messages $argv[1] | \
        fzf $FZF_CUSTOM_PARAMS \
            --preview-window right:70%:rounded:hidden:wrap \
            --header="$(_buildFzfHeader '' 'fzf_search_term')" \
            --preview "highlight -O ansi -l {} 2> /dev/null | rg --colors 'match:bg:yellow' --ignore-case --pretty --context 10 '$argv[1]' || rg --ignore-case --pretty --context 10 '$argv[1]' {}"
end
alias fst="fzf_search_term"

function list_link_files
    set mpath './'
    if test -n $argv[1]
        set mpath $argv[1]
    end
    /bin/ls -al $mpath | grep ^l
end
alias llf="list_link_files"

function fzf_find_link_files
    set mpath './'
    if test -n $argv[1]
        set mpath $argv[1]
    end
    /usr/bin/find $mpath -type l -ls | fzf $FZF_CUSTOM_PARAMS --header="$(_buildFzfHeader '' 'fzf_aliases')"
end
alias fflf="fzf_find_link_files"

function file_category
    if test -z $argv[1]
        return 1
    end
    set mime (file -bL --mime-type $argv[1])
    echo $mime[1..(string match -r '/' $mime) - 1]
    return 0
end
alias fcate="file_category"

function file_kind
    if test -z $argv[1]
        return 1
    end
    set mime (file -bL --mime-type $argv[1])
    echo $mime[(string match -r '/' $mime) + 1..-1]
    return 0
end
alias fkind="file_kind"
