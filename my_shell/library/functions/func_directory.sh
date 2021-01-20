function cd() { # Desc: cd命令后列出目录内容
    builtin cd "$@"; /usr/local/bin/gls -aGH --color=tty;
}

function customcd() { # Desc: 自定义cd命令
    builtin cd "$@";
}

function fda() { # Desc: including hidden directories
    DIR=`find ${1:-.} -type d 2> /dev/null | fzf-tmux` && cd "$DIR"
}

function mcdf () { # Desc: short for cdfinder
    cd "`osascript -e 'tell app "Finder" to POSIX path of (insertion location as alias)'`"
}

function hideF() { # Desc: 文件夹不显示隐藏文件
    defaults write com.apple.Finder AppleShowAllFiles NO ; killall Finder /System/Library/CoreServices/Finder.app;
}

function showF() { # Desc: 文件夹显示隐藏文件
    defaults write com.apple.Finder AppleShowAllFiles YES ; killall Finder /System/Library/CoreServices/Finder.app;
}

function fdr() { # Desc: fdr - cd to selected parent directory
    local declare dirs=()
    function get_parent_dirs() {
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

function fcd() { # Desc: cd to selected directory
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

# fzf (https://github.com/junegunn/fzf)
# --------------------------------------------------------------------

function fd2() { # Desc: another cd to selected directory
    DIR=`find ${1:-*} -path '*/\.*' -prune -o -type d -print 2> /dev/null | fzf-tmux` \
        && cd "$DIR"
}

function cdff() { # Desc: cdff - cd into the directory of the selected file
    local file
    local dir
    file=$(fzf +m -q "$1") && dir=$(dirname "$file") && cd "$dir"
}

function gdto() { # Desc: cd 包含参数的名称的文件夹
    [ "$1" ] && cd *$1*
}

function dirw() { # Desc: 获取命令所在目录
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        echo $(dirname "$@");
    else
        echo $(dirname $(type "$@" | awk '{print $NF}'));
    fi
}

function parentdir() { # Desc: 获取父级目录
    echo $(dirname "$@");
}

function mcd () { # Desc: Makes new Dir and jumps inside
    mkdir -p "$1" && cd "$1";
}        # mcd:          Makes new Dir and jumps inside

function cdpw() { # Desc: cd 命令所在的父级文件夹
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        cd `dirname $(dirname $(which "$1"))`
    else
        cd $(dirname $(dirname $(type "$1" | awk '{print $NF}')))
    fi
}

function cdw() { # Desc: cd 命令所在的文件夹
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        cd `dirname $(which "$1")`
    else
        cd $(dirname $(type "$1" | awk '{print $NF}'))
    fi
}

function cdto() { # Desc: cd 命令所在的文件夹
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        cd `dirname $(which "$1")`
    else
        cd $(dirname $(type "$1" | awk '{print $NF}'))
    fi
}

function fz() { # Desc: 目录跳转
    [ $# -gt 0 ] && fasd_cd -d "$*" && return
    local dir
    dir="$(fasd -Rdl "$1" | fzf -1 -0 --no-sort +m)" && cd "${dir}" || return 1
}

function llw() { # Desc: ll 打印which命令找到的文件地址
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        ls -l  `which "$1"`
    else
        ls -l  $(type "$1" | awk '{print $NF}')
    fi
}

function openw() { # Desc: open 打开which命令找到的目录或文件
    command -v "$@" > /dev/null 2>&1
    [[ "$?" = "1" ]] && echo "Command $@ does not exists !" && return 1
    if [ "$(type $1 | grep 'a shell function from')" = "" ]; then
        open `dirname $(which "$1")`
    else
        open $(dirname $(type "$1" | awk '{print $NF}'))
    fi
}