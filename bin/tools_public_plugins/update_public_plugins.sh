#!/bin/bash
PUBLICPATH=$(cat ~/.myruntime)/public
GITBIN=/usr/local/bin/git


if [ -d $PUBLICPATH ]; then
	plugins=$(ls -A $PUBLICPATH | grep -v "tools_public_plugins")
	if [ "" != "$plugins" ]; then
		echo "时间很漫长，请耐心等待..."
		i=0
		for plugin in $plugins; do
			echo "$i --- $plugin" > $PUBLICPATH/tools_public_plugins/curplugin
			cd $PUBLICPATH/$plugin && $GITBIN pull >> /dev/null
			((i+=1))
		done
		echo "更新完成"
		exit 0
	fi
else
	echo "插件集合目录不存在"
	exit 1
fi
