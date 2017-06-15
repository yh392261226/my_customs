#!/bin/bash
#RUNTIME目录
RUNTIMEPATH=$(cat ~/.myruntime)
#VIM配置文件夹结尾
VIMEXT=vimfiles
#VIM配置文件夹中的第二层文件夹名称
VIMSECPATH=(vim .vim)
#插件目录
PLUGINPATH=(plugged bundle plugin plugins)
#公共插件目录
PUBLICPATH=$RUNTIMEPATH/public
#git命令地址
GITBIN=/usr/local/bin/git


###软连接 $1 -> $2 且$2会被先删除再链接
symlink() {
    public=$1
    filepath=$2

    if [ -d $public ]; then #插件目录必须存在
        if [ -d $filepath ]; then #链接目标需要不存在
            rm -rf $filepath
        fi
        /bin/ln -sf $public $filepath
    fi
    return 0
}

###获取插件下的.git/config文件中的地址 并丰富到共享插件目录 然后软连接到使用目录
getCloneByConfig() {
    filepath=$1
    if [ -d $filepath ]; then
        if [ -f $filepath/.git/config ]; then #验证.git的config文件是否存在
            tmpurl=$(cat $filepath/.git/config | grep "url = " |awk -F "url = " '{print $2}')
            if [ "" != "$(echo $tmpurl | grep 'github.com/')" ]; then #过滤github.com/
                url=$(echo $tmpurl | grep 'github.com/' | awk -F 'github.com/' '{print $2}' | sed 's,.git,,')
            elif [ "" != "$(echo $tmpurl | grep 'github.com:')" ]; then #过滤github.com:
                url=$(echo $tmpurl | grep 'github.com:' | awk -F 'github.com:' '{print $2}' | sed 's,.git,,')
            fi
            if [ "" != "$url" ]; then
                url=$(echo $url | sed 's,https://,,' | sed 's,git://,,' | sed 's,/,_,') # 过滤https:// git:// 并 / 转 _
                if [ ! -d $PUBLICPATH/$url ]; then
                    echo "$GITBIN clone $tmpurl $PUBLICPATH/$url" >> $PUBLICPATH/didnot.log
                    $GITBIN clone $tmpurl $PUBLICPATH/$url
                fi
                symlink $PUBLICPATH/$url $filepath
            fi
        fi
    fi
}

###按步骤执行
if [ -d $RUNTIMEPATH ]; then #判断runtime文件夹是否存在
    configs=$(ls $RUNTIMEPATH | grep "$VIMEXT")
    if [ "" != "$configs" ]; then #判断配置文件夹是否存在
        for config in $configs; do #循环所有的配置文件夹
            for file in ${VIMSECPATH[@]}; do #循环所有的第二层文件夹
                if [ -f $RUNTIMEPATH/$config/$file ] || [ -d $RUNTIMEPATH/$config/$file ]; then
                    config_sec_path=$RUNTIMEPATH/$config/$file
                else
                    config_sec_path=$RUNTIMEPATH/$config
                fi
            done
            if [ -d $config_sec_path ]; then #验证二级目录
                for plugin in ${PLUGINPATH[@]}; do
                    if [ -d $config_sec_path/$plugin ]; then #二级目录下的插件文件夹指定
                        config_sec_plugin=$config_sec_path/$plugin
                        break 1
                    fi
                done
                if [ -d $config_sec_plugin ]; then #验证二级目录下插件目录是否存在
                    curplugins=$(ls $config_sec_plugin)
                    if [ "" != "$curplugins" ]; then #验证当前插件目录下是否为空
                        for curplugin in $curplugins; do
                            if [ -d $config_sec_plugin/$curplugin ] && [ ! -L $config_sec_plugin/$curplugin ]; then #验证是文件夹且不能是软连接
                                echo $config_sec_plugin/$curplugin #得到文件名
                                getCloneByConfig $config_sec_plugin/$curplugin
                            fi
                        done
                    fi
                else
                    echo "二级目录下的插件目录不存在，检测有误"
                    exit 1
                fi
            else
                echo "二级目录不存在，检测有误"
                exit 1
            fi
        done
    else
        echo "未发现配置文件夹"
        exit 1
    fi
else
    echo "RUNTIME目录不存在"
    exit 1
fi
