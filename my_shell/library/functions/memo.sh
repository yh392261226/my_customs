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