# Desc: speaking the words you type in with osx voice:ting ting
function speaking() {
    words=$1
    if [ $# -ne 1 ]; then
        echo "请输入要说的话"
        echo "例如：$0 haha "
        return 1
    fi
    #osascript -e 'say "'$words'" using "Cellos"'
    osascript -e 'say "'$words'" using "Ting-Ting"'
}
