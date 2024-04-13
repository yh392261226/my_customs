function remove_DS_files
    if test -z $argv
        find . -type f -name '*.DS_Store' -ls -delete
    else
        find $argv -type f -name '*.DS_Store' -ls -delete
    end
end
alias rDS remove_DS_files

function remove_files_by_ext
    if test -z $argv
        trash ./*
    else
        trash ./*$argv
    end
end
alias rfe remove_files_by_ext

function remove_ssh_tmp_file
    /bin/rm -f $HOME/.ssh/tmp/*
end
alias rst remove_ssh_tmp_file

function remove_to_trash
    for mpath in $argv
        if test (string match -q -* $mpath)
            continue
        end

        set dst (basename $mpath)
        while test -e $HOME/.Trash/$dst
            set dst "$dst "(date +%H-%M-%S)
        end

        /bin/mv $mpath $HOME/.Trash/$dst
    end
end
alias r2t remove_to_trash

function trash
    command /bin/mv $argv $HOME/.Trash
end
alias t trash

function remove_whereis_file
    command -v $argv > /dev/null 2>&1
    if test $status != 0
        echo "Command $argv does not exist !"
        return 1
    end

    if test (type $argv | grep 'a shell function from') = ""
        if test (type $argv | grep 'is an alias for') = ""
            rm -f (which $argv)
        else
            set endfile (type $argv | awk '{print $NF}')
            if test -f $endfile
                rm -f $endfile
            else
                remove_whereis_file $endfile
            end
        end
    end
end
alias rmw remove_whereis_file

function fzf_remove_file
    set hasgum (ifHasCommand gum)

    if test (count $argv) -eq 0
        set files (find . -maxdepth 1 -type f | fzf --multi $FZF_CUSTOM_PARAMS --header=(_buildFzfHeader '' 'fzf_remove_file') --preview-window right:70%:rounded:hidden:wrap --preview " $MYRUNTIME/customs/bin/_previewer {} ")
        if test -z $files
            return 1
        end
        if test $hasgum = 1
            gum confirm "确认删除?" and echo $files | xargs -I '{}' rm {} or echo "Action aborted !"
        else
            echo $files | xargs -I '{}' rm {}
        end
    else
        if test $hasgum = 1
            gum confirm "确认删除?" and command rm $argv or echo "Action aborted !"
        else
            command rm $argv
        end
    end
end
alias frf fzf_remove_file

function fzf_remove_directory
    set hasgum (ifHasCommand gum)

    if test (count $argv) -eq 0
        set directories (find . -maxdepth 1 -type d | fzf --multi $FZF_CUSTOM_PARAMS --header=(_buildFzfHeader '' 'fzf_remove_directory') --preview-window right:70%:rounded:hidden:wrap --preview " $MYRUNTIME/customs/bin/_previewer {} ")
        if test -z $directories
            return 1
        end
        if test $hasgum = 1
            gum confirm "确认删除?" and echo $directories | xargs -I '{}' rm -rf {} or echo "Action aborted !"
        else
            echo $directories | xargs -I '{}' rm -rf {}
        end
    else
        if test $hasgum = 1
            gum confirm "确认删除?" and command rm -rf $argv or echo "Action aborted !"
        else
            command rm -rf $argv
        end
    end
end
alias frd fzf_remove_directory
