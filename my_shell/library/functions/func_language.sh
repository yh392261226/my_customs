# Desc: RVM integration
function frb() {
    local rb
    rb=$(
    (echo system; rvm list | grep ruby | cut -c 4-) |
    awk '{print $1}' |
    fzf-tmux -l 30 +m --reverse) && rvm use $rb
}

# Desc: rvm多个版本的gem操作同一个包
function gems() {
    for v in 2.0.0 1.8.7 jruby 1.9.3; do
        rvm use $v
        gem $@
    done
}

# Desc: rvm多个版本的rake操作同一个包
function rakes() {
    for v in 2.0.0 1.8.7 jruby 1.9.3; do
        rvm use $v
        rake $@
    done
}



#   mans:   Search manpage given in agument '1' for term given in argument '2' (case insensitive)
#           displays paginated result with colored search terms and two lines surrounding each hit.             Example: mans mplayer codec
#   --------------------------------------------------------------------

# Desc: man command[$1] and highlight keyword[$2]
function mans () {
    man $1 | grep -iC2 --color=always $2 | less
}

# Desc: 依托于cheat.sh的备忘录
function memo() {
    if [ $# -lt 1 ]; then
        echo "Usage:$0 language function"
        echo ""
        echo "---------------------------------------"
        echo ""
        curl cht.sh
        return 0
    fi


    url="cheat.sh/"
    if [ "$1" != "" ]; then
        url="cheat.sh/$1/"
    fi

    if [ "$2" != "" ]; then
        url="cheat.sh/$1/$2"
    fi

    if [ "$3" != "" ]; then
        url="cheat.sh/$1/$2+$3"
    fi
    curl $url
}

