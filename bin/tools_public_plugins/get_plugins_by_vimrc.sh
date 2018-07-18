#!/bin/bash
################################
### 把所有的插件都列出到 log文件
### 会有一些垃圾文件需要手动清理
################################
RUNTIMEPATH=$(cat ~/.myruntime)
EXT=vimfiles

for i in $(ls $RUNTIMEPATH | grep "$EXT"); do
	configfile=""
	if [ -f $RUNTIMEPATH/$i/vimrc ]; then
		configfile=$RUNTIMEPATH/$i/vimrc
	elif [ -f $RUNTIMEPATH/$i/.vimrc ]; then
		configfile=$RUNTIMEPATH/$i/.vimrc
	fi

	if [ "$configfile" != "" ]; then
		cat $configfile | grep 'Plug \|Bundle \|NeoBundle'  >> ./log #| awk '{print $2}'
	fi
done

if [ -f ./log ]; then
	cat ./log | awk '{print $2}' | sed "s,\',," | sed 's,\",,' | sort | uniq | sort -nr > ./uniq_log
fi

for i in $(cat ./uniq_log); do
	if [ "$(echo $i |grep 'git:')" != "" ]; then
		landfilename=$(echo $i|sed "s,://,,"|cut -d "/" -f 2)_$(echo $i|sed "s,://,,"|cut -d "/" -f 3)
		landfilename=$(echo $landfilename |sed "s,\.git,,")
		cd $RUNTIMEPATH/public/ && git clone $i $landfilename
	else
		landfilename=$(echo $i|sed "s,/,_,")
		cd $RUNTIMEPATH/public/ && git clone https://github.com/$i $landfilename
	fi
done
