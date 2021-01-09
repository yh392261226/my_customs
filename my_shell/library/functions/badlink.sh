# Desc: check out the bad links
function badlink() {
    local readpath=$HOME
    if [ "" != "$1" ]; then
        readpath=$1
    fi
    echo "File List broken links:"
    for file in $(ls -a $readpath); do
    realpath=$(/usr/bin/readlink $readpath/$file)
    if [ ! -f $realpath ] && [ ! -d $realpath ]; then
        echo $readpath/$file
    fi
    done
}