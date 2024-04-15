function remove_DS_files
    if test -z $argv
        find . -type f -name '*.DS_Store' -ls -delete
    else
        find $argv -type f -name '*.DS_Store' -ls -delete
    end
end
alias rDS="remove_DS_files"

function remove_files_by_ext
    if test -z $argv
        trash ./*
    else
        trash ./*$argv
    end
end
alias rfe="remove_files_by_ext"

function remove_ssh_tmp_file
    /bin/rm -f $HOME/.ssh/tmp/*
end
alias rst="remove_ssh_tmp_file"

function remove_to_trash
    for mpath in $argv
        if string match -q -- '-*' $mpath
            continue
        end

        set dst (basename $mpath)
        while test -e $HOME/.Trash/$dst
            set dst "$dst "(date +%H-%M-%S)
        end

        /bin/mv $mpath $HOME/.Trash/$dst
    end
end
alias r2t="remove_to_trash"

function trash
    command /bin/mv $argv $HOME/.Trash
end
alias t="trash"

function remove_whereis_file
    if not test (ifHasCommand $argv) = "1"
        echo "Command $argv does not exists !"
        return 1
    end

    if test -n (type "$argv[1]" | grep 'a function with definition'); and test -n (type "$argv[1]" | grep 'a alias')
        rm -f (which "$argv[1]")
    else
        set endfile (type "$argv[1]" | awk '{print $NF}')
        if test -f $endfile
            rm -f $endfile
        else
            remove_whereis_file $endfile
        end
    end
end
alias rmw="remove_whereis_file"

function fzf_remove_file

    if test (count $argv) -eq 0
        set files (find . -maxdepth 1 -type f | fzf --multi $FZF_CUSTOM_PARAMS --header=(_buildFzfHeader '' 'fzf_remove_file') --preview-window right:70%:rounded:hidden:wrap --preview " $MYRUNTIME/customs/bin/_previewer_fish {} ")
        if test "" = "$files"
            return 1
        end
        if test (ifHasCommand gum) = "1"
            if not test (gum confirm '确认删除?'; echo $status) -eq 1
                rm -f $files
            else
                echo "Action aborted !"
            end
        else
            rm -f $files
        end
    else
        if test (ifHasCommand gum) = "1"
            if not test (gum confirm '确认删除?'; echo $status) -eq 1
                rm -f $argv
            else
                echo "Action aborted !"
            end
        else
            rm -f $argv
        end
    end
end
alias frf="fzf_remove_file"

function fzf_remove_directory
    if test (count $argv) -eq 0
        set directories (find . -maxdepth 1 -type d | fzf --multi $FZF_CUSTOM_PARAMS --header=(_buildFzfHeader '' 'fzf_remove_directory') --preview-window right:70%:rounded:hidden:wrap --preview " $MYRUNTIME/customs/bin/_previewer_fish {} ")
        if test "" = "$directories"
            return 1
        end
        if test (ifHasCommand gum) = "1"
            if not test (gum confirm '确认删除?'; echo $status) -eq 1
                rm -rf $directories
            else
                echo "Action aborted !"
            end
        else
            echo $directories | xargs -I '{}' rm -rf {}
        end
    else
        if test (ifHasCommand gum) = "1"
            if not test (gum confirm '确认删除?'; echo $status) -eq 1
                rm -rf $argv
            else
                echo "Action aborted !"
            end
        else
            rm -rf $argv
        end
    end
end
alias frd="fzf_remove_directory"
