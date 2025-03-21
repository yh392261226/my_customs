function cd
    if not command -q lsd
        builtin cd $argv; gls -aGH --color=tty
    else
        builtin cd $argv; lsd -l
    end
    if python3 -m fzfdirhist > /dev/null ^&1
        python3 -m fzfdirhist log (pwd)
    end
end

function customcd
    command cd $argv
end

function fzf_cd_to
    if test -z $argv
        echo "ex: fct word1 word2"
        return 1
        exit 1
    end

    set file (glocate -Ai -0 $argv | grep -z -vE '~$' | fzf $FZF_CUSTOM_PARAMS --read0 -0 -1 --header=(_buildFzfHeader '' 'fzf_cd_to') --preview='$MYRUNTIME/customs/bin/_previewer_fish {}' --preview-window right:70%:rounded:hidden:wrap)
    if test -n $file
        if test -d $file
            cd -- $file
        else
            cd -- $file:h
        end
    end
end
alias fct="fzf_cd_to"

function fzf_hidden_directories
    if not test "$argv" = ""
        set findpath "$argv"
    else
        set findpath (pwd)
    end
    set DIR (find $findpath -type d -name '.*' | fzf-tmux $FZF_CUSTOM_PARAMS --header-first --header=(_buildFzfHeader '' 'fzf_hidden_directories') --preview="$MYRUNTIME/customs/bin/_previewer_fish {}" --preview-window='right:70%:rounded:hidden:wrap')
    if not test "$DIR" = ""
        cd $DIR
    end
end
alias fhd="fzf_hidden_directories"

function change_files_hide
    defaults write com.apple.Finder AppleShowAllFiles NO; killall Finder /System/Library/CoreServices/Finder.app
end
alias cfh="change_files_hide"

function change_files_show
    defaults write com.apple.Finder AppleShowAllFiles YES; killall Finder /System/Library/CoreServices/Finder.app
end
alias cfs="change_files_show"


function fzf_cd_to_parent
    set -g dirs
    function _get_parent_dirs
        if test -d $argv[1]
            set -l dir $argv[1]
            set -g dirs $dirs $dir
        else
            return
        end

        if test $argv[1] = "/"
            for dir in $dirs
                echo $dir
            end
        else
            _get_parent_dirs (dirname $argv[1])
        end
    end
    if not test "$argv" = ""
        set -l cdpath $argv
    else
        set -l cdpath (pwd)
    end

    set DIR (_get_parent_dirs (realpath $cdpath) | fzf-tmux $FZF_CUSTOM_PARAMS --tac --header=(_buildFzfHeader '' 'fzf_cd_to_parent'))
    set -x dirs
    if not test "$DIR" = ""
        cd $DIR
    end
end
alias fc2p="fzf_cd_to_parent"

function fzf_cd_to_select
    if test (count $argv) != 0
        cd $argv
        return
    end

    while true
        set lsd (echo ".."; ls -p | grep '/$' | sed 's;/$;;')
        set dir (printf '%s\n' $lsd | fzf $FZF_CUSTOM_PARAMS --preview-window right:70%:rounded:hidden:wrap --preview '
            __cd_nxt="$(echo {})"; 
            __cd_path="$(echo (pwd)/${__cd_nxt} | sed "s;//;/")"; 
            echo $__cd_path; 
            echo; 
            gls -p --color=always "${__cd_path}";
        ' --header=(_buildFzfHeader '' 'fzf_cd_to_select'))

        if test (count $dir) != 0
            cd $dir > /dev/null
        else
            return 0
        end
    end
end
alias fcd="fzf_cd_to_select"

function fzf_cd_to_select2
    if not test "$argv" = ""
        set findpath $argv
    else
        set findpath (pwd)
    end
    set DIR (find $findpath -type d | fzf-tmux --header-first --header=(_buildFzfHeader '' 'fzf_cd_to_select2'))
    if not test -n $DIR
        cd $DIR
    end
end
alias fcd2="fzf_cd_to_select2"

function fzf_cd_to_file
    set file (find (pwd) -type f | fzf +m $FZF_CUSTOM_PARAMS --preview-window right:70%:rounded:hidden:wrap --preview='$MYRUNTIME/customs/bin/_previewer_fish {}' --preview-window right:70%:rounded:hidden:wrap --header=(_buildFzfHeader '' 'fzf_cd_to_file') -q "$argv") 
    if not test "$file" = ""
        set dir (dirname $file)
        cd $dir
    end
end
alias fc2f="fzf_cd_to_file"

function cd_directory_by_param
    if not test "$argv" = ""
        cd "*$argv*"
    end
end
alias cdbp="cd_directory_by_param"

function get_which_command_directory
    if not test (ifHasCommand $argv) = "1"
        echo "Command $argv does not exists !"
        return 1
    end

    if not string match -q "a function with definition" (type $argv)
        echo (dirname $argv)
    else
        set endfile (type $argv | awk '{print $NF}')
        if test -f $endfile
            echo (dirname $endfile)
        else
            get_which_command_directory $endfile
        end
    end
end
alias dirw="get_which_command_directory"

function get_parent_directory
    echo (dirname $argv)
end
alias gpd="get_parent_directory"

function mkdir_cd
    mkdir -p $argv; cd $argv
end
alias mcd="mkdir_cd"

function cd_parent_directory_by_which_command
    if not test (ifHasCommand $argv) = "1"
        echo "Command $argv does not exist !"
        return 1
    end

    if not string match -q "a function with definition" (type $argv)
        cd (dirname (dirname (which $argv)))
    else
        set endfile (type $argv | awk '{print $NF}')
        if test -f $endfile
            cd (dirname (dirname $endfile))
        else
            cd_parent_directory_by_which_command $endfile
        end
    end
end
alias cdpw="cd_parent_directory_by_which_command"

function cd_directory_by_which_command
    if test -f $argv
        cd (dirname $argv); return 1
    end
    if test -d $argv
        cd $argv; return 1
    end

    if not test (ifHasCommand $argv) = "1"
        echo "Command $argv does not exist !"
        return 1
    end

    if not string match -q "a function with definition" (type $argv)
        cd (dirname (which $argv))
    else
        set endfile (type $argv | awk '{print $NF}')
        if test -f $endfile
            cd (dirname $endfile)
        else
            cd_directory_by_which_command $endfile
        end
    end
end
alias cdw="cd_directory_by_which_command"

function fzf_jump_between_directory
    if test (count $argv) -gt 0
        fasd_cd -d $argv; return
    end

    set dir (fasd -Rdl $argv | fzf -1 -0 --no-sort +m $FZF_CUSTOM_PARAMS --preview='$MYRUNTIME/customs/bin/_previewer_fish {}' --preview-window right:70%:rounded:hidden:wrap --header=(_buildFzfHeader '' 'fzf_jump_between_directory'))
    if test -n $dir
        cd $dir
    else
        return 1
    end
end
alias fz="fzf_jump_between_directory"

function ll_whereis_command
    if not test (ifHasCommand $argv) = "1"
        echo "Command $argv does not exist !"
        return 1
    end

    if not string match -q "a function with definition" (type $argv) && not string match -q "is an alias for" (type $argv)
        ls -l (which $argv)
    else
        set endfile (type $argv | awk '{print $NF}')
        if test -f $endfile
            ls -l $endfile
        else
            ll_whereis_command $endfile
        end
    end
end
alias llw="ll_whereis_command"

function open_directory_whereis_command
    if not test (ifHasCommand $argv) = "1"
        echo "Command $argv does not exist !"
        return 1
    end

    if not string match -q "a function with definition" (type $argv) && not string match -q "is an alias for" (type $argv)
        open (dirname (which $argv))
    else
        set endfile (type $argv | awk '{print $NF}')
        if test -f $endfile || test -d $endfile
            open (dirname $endfile)
        else
            open_directory_whereis_command $endfile
        end
    end
end
alias openw="open_directory_whereis_command"

function pwd_command_directory
    if not test (ifHasCommand $argv) = "1"
        echo "Command $argv does not exist !"
        return 1
    end

    if not string match -q "a function with definition" (type $argv) && not string match -q "is an alias for" (type $argv)
        echo (dirname (which $argv))
    else
        set endfile (type $argv | awk '{print $NF}')
        if test -f $endfile
            echo (dirname $endfile)
        else
            pwd_command_directory $endfile
        end
    end
end
alias pwdw="pwd_command_directory"

function fzf_directory_history
    set dir (python3 -m fzfdirhist show | fzf $FZF_CUSTOM_PARAMS +m --preview='$MYRUNTIME/customs/bin/_previewer_fish {}' --preview-window right:70%:rounded:hidden:wrap --header=(_buildFzfHeader '' 'fzf_directory_history'))
    cd $dir
end
alias fdh="fzf_directory_history"
