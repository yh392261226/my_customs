# Desc:tmux 根据选择使用配置文件
function tmuxf() {
    local CONFIGS=$MYRUNTIME/tmuxconfigs  #配置文件地址
    local EXT=tmux.conf

    if [ -d $CONFIGS ]; then
        local configs=($(ls $CONFIGS/*${EXT}))
        if [ "${#configs[*]}" != "0" ]; then
            echo "Input the NO. :";
            local posit=0
            for file in ${configs[*]}; do
                echo $posit "：" $(basename ${file} | awk -F ".$EXT" '{print $1}');
                ((posit+=1))
            done
            #echo ${configs[2]}
            read conf
            if [ "$conf" -lt "${#configs[*]}" ]; then
                /usr/local/bin/tmux -f ${configs[$conf]}
                return 0
            else
                echo "The config you choose does not exists ！！！";
                return 1
            fi
        else
            echo "No config can be found ！！！";
            return 1
        fi
    else
        echo "Path of config does not exists ！！！";
        return 1
    fi
}