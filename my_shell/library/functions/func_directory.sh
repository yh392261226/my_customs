function cd() { # Desc: cd:cd命令后列出目录内容
    builtin cd "$@"; gls -aGH --color=tty;
}

function customcd() { # Desc:customcd:自定义cd命令
    builtin cd "$@";
}

function fzf_cd_to() { # Desc: fzf_cd_to: fuzzy cd from anywhere. ex: fcf word1 word2 ... (even part of a file name)
    local file
    file="$(locate -Ai -0 $@ | grep -z -vE '~$' | fzf --read0 -0 -1)"
    if [[ -n $file ]]
    then
        if [[ -d $file ]]
        then
            cd -- $file
        else
            cd -- ${file:h}
        fi
    fi
}
alias fcf="fzf_cd_to"

function fzf_hidden_directories() { # Desc: fzf_da:including hidden directories
    DIR=`find ${1:-.} -type d 2> /dev/null | fzf-tmux` && cd "$DIR"
}
alias fda="fzf_hidden_directories"

function mcdf() { # Desc: mcdf:short for cdfinder
    cd "`osascript -e 'tell app "Finder" to POSIX path of (insertion location as alias)'`"
}

function hidden_files_hide() { # Desc: hidden_files_hide:文件夹不显示隐藏文件
    defaults write com.apple.Finder AppleShowAllFiles NO ; killall Finder /System/Library/CoreServices/Finder.app;
}
alias hideF="hidden_files_hide"

function hidden_files_show() { # Desc: hidden_files_show:文件夹显示隐藏文件
    defaults write com.apple.Finder AppleShowAllFiles YES ; killall Finder /System/Library/CoreServices/Finder.app;
}
alias showF="hidden_files_show"

function fzf_cd_to_parent() { # Desc: fzf_cd_to_parent:cd to selected parent directory
    local declare dirs=()
    get_parent_dirs() {
        if [[ -d "${1}" ]]; then dirs+=("$1"); else return; fi
        if [[ "${1}" == '/' ]]; then
            for _dir in "${dirs[@]}"; do echo $_dir; done
        else
            get_parent_dirs $(dirname "$1")
        fi
    }
    local DIR=$(get_parent_dirs $(realpath "${1:-$PWD}") | fzf-tmux --tac)
    cd "$DIR"
}
alias fdr="fzf_cd_to_parent"

function fzf_cd_select() { # Desc: fzf_cd:cd to selected directory
    if [[ "$#" != 0 ]]; then
        builtin cd "$@";
        return
    fi
    while true; do
        local lsd=$(echo ".." && ls -p | grep '/$' | sed 's;/$;;')
        local dir="$(printf '%s\n' "${lsd[@]}" |
            fzf --reverse --preview '
                __cd_nxt="$(echo {})";
                __cd_path="$(echo $(pwd)/${__cd_nxt} | sed "s;//;/;")";
                echo $__cd_path;
                echo;
                gls -p --color=always "${__cd_path}";
        ')"
        [[ ${#dir} != 0 ]] || return 0
        builtin cd "$dir" &> /dev/null
    done
}
alias fcd="fzf_cd_select"

# fzf (https://github.com/junegunn/fzf)
function fzf_cd_select2() { # Desc: fzf_cd_select2:another cd to selected directory
    DIR=`find ${1:-*} -path '*/\.*' -prune -o -type d -print 2> /dev/null | fzf-tmux` \
        && cd "$DIR"
}
alias fd2="fzf_cd_select2"

function fzf_cd_to_file() { # Desc: fzf_cd_to_file:cd into the directory of the selected file
    local file
    local dir
    file=$(fzf +m -q "$1") && dir=$(dirname "$file") && cd "$dir"
}
alias cdff="fzf_cd_to_file"

function cd_like_directory() { # Desc: gdto:包含参数的名称的文件夹
    [ "$1" ] && cd *$1*
}
alias gdto="cd_like_directory"

function get_command_directory() { # Desc: dirw:获取命令所在目录
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        echo $(dirname "$@");
    else
        echo $(dirname $(type "$@" | awk '{print $NF}'));
    fi
}
alias dirw="get_command_directory"

function get_parent_directory() { # Desc: get_parent_directory:获取父级目录
    echo $(dirname "$@");
}
alias parentdir="get_parent_directory"

function mkdir_cd() { # Desc: mcd:创建文件夹并进入
    mkdir -p "$1" && cd "$1";
}
alias mcd="mkdir_cd"

function cd_command_parent_directory() { # Desc: cd_command_parent_directory:命令所在的父级文件夹
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        cd `dirname $(dirname $(which "$1"))`
    else
        cd $(dirname $(dirname $(type "$1" | awk '{print $NF}')))
    fi
}
alias cdpw="cd_command_parent_directory"

function cd_command_directory() { # Desc: cd_command_directory:命令所在的文件夹
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        cd `dirname $(which "$1")`
    else
        cd $(dirname $(type "$1" | awk '{print $NF}'))
    fi
}
alias cdw="cd_command_directory"
alias cdto="cd_command_directory"

function fzf_jump_between_directory() { # Desc: fzf_z:目录跳转
    [ $# -gt 0 ] && fasd_cd -d "$*" && return
    local dir
    dir="$(fasd -Rdl "$1" | fzf -1 -0 --no-sort +m)" && cd "${dir}" || return 1
}
alias fzf_z="fzf_jump_between_directoryf"
alias fz="fzf_jump_between_directory"

function ll_whereis_command() { # Desc: ll_whereis_command:打印which命令找到的文件地址
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        ls -l  `which "$1"`
    else
        ls -l  $(type "$1" | awk '{print $NF}')
    fi
}
alias llw="ll_whereis_command"

function open_directory_whereis_command() { # Desc: openw:打开which命令找到的目录或文件
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        open `dirname $(which "$1")`
    else
        open $(dirname $(type "$1" | awk '{print $NF}'))
    fi
}
alias openw="open_directory_whereis_command"