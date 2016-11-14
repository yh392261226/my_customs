#!/bin/bash
###########################################################
### 将已有的目录下所有插件去插件集目录软连接过来 
### link the vim plugins from the custom/public/ to save the disk, if the plugin does not in the custom/public, it will auto download by the .git/config url=
### Usage: ./other_plugins_symlink.sh the_current_vim/plugged|bundle...
###########################################################

PUBLICPATH=/Users/json/.runtime/public    	#插件集合目录
GITBIN=/usr/local/bin/git					#git命令地址

if [ -d $PUBLICPATH ]; then #插件集合目录必须存在
	if [ $# -ne 1 ]; then
		echo "使用方法: $0 全目录名称"
		exit 1
	fi

	if [ -d $1 ]; then #第一个参数即当前路径必须存在
		plugins=$(ls -A $1)
		if [ "" != "$plugins" ]; then #插件必须有
			for plugin in $plugins; do
				if [ -d $1/$plugin ] && [ ! -L $1/$plugin ]; then #需要是目录 不能影响到别的软连接
					plugin_git=$(cat $plugin/.git/config | grep "url = " | awk -F "url = " '{print $2}')
					url=$plugin_git
					if [ "" != "$plugin_git" ]; then #如果没有git的插件跳过
						if [ "" != "$(echo $plugin_git | grep 'github.com/')" ]; then #过滤github.com/
                			plugin_git=$(echo $plugin_git | grep 'github.com/' | awk -F 'github.com/' '{print $2}' | sed 's,.git,,')
            			elif [ "" != "$(echo $plugin_git | grep 'github.com:')" ]; then #过滤github.com:
                			plugin_git=$(echo $plugin_git | grep 'github.com:' | awk -F 'github.com:' '{print $2}' | sed 's,.git,,')
            			fi
						if [ "" != "$plugin_git" ]; then #
            			    plugin_git=$(echo $plugin_git | sed 's,https://,,' | sed 's,git://,,' | sed 's,/,_,') # 过滤https:// git:// 并 / 转 _
            			    if [ ! -d $PUBLICPATH/$plugin_git ]; then
            			        $GITBIN clone $url $PUBLICPATH/$plugin_git
            			    fi
							rm -rf $1/$plugin && ln -sf $PUBLICPATH/$plugin_git $1/$plugin
            			fi
					else
						continue
					fi
				fi
			done
		else
			echo "参数目录中无插件"
			exit 1
		fi
	else
		echo "参数目录不存在"
		exit 1
	fi
else
	echo "插件集合目录不存在"
	exit 1
fi
