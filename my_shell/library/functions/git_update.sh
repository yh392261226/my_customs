# Desc: 更新git的目录及git module的目录
function upgitfiles() {
    if [ "" != "$1" ]; then
        filepath=$1
    else
        filepath=$MYRUNTIME
    fi

    for f in $(/bin/ls $filepath/); do
        if [ -d $filepath/$f/.git ]; then
            echo $filepath/$f
            customcd $filepath/$f/ && /usr/bin/git pull
        fi
        if [ -f $filepath/$f/.gitmodules ]; then
            echo $filepath/$f
            customcd $filepath/$f/ && /usr/bin/git submodule update --init --recursive
        fi
    done
    customcd ~
}