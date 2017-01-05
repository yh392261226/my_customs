#!/bin/bash
##
## 根据不同的网络位置设置 改变当前背景图片的读取位置
## beyond the diffrent posit of network link the diffrent image path to the picture
## you should set the network positions of osx first
##
CURLOCATION=$(networksetup -getcurrentlocation);  #当前位置名
PICURL=$MYRUNTIME/pictures; #图片软连接地址
CURMARKFILE=$MYRUNTIME/tools/positmark
COMPANYPICS=$HOME/Pictures/down_pics/company
OTHERPICS=$HOME/Pictures/down_pics/pictures



changepiclink() {
    rm -f $PICURL;
    ln -sf $1 $PICURL;
    return 1;
}

hastochange() {
    curmark=$(cat $CURMARKFILE);
    if [ "$1" = "$curmark" ];then
        exit 1;
    fi
}

case "$CURLOCATION" in
    company) #公司
        hastochange company;
        text="公司哟，亲！注意注意！！！";
        echo "company" > $CURMARKFILE;
        changepiclink $COMPANYPICS;
    ;;
    home) #自己家
        hastochange home;
        text="自己家哟，亲！随意哟！！！";
        echo "home" > $CURMARKFILE;
        changepiclink $OTHERPICS;
    ;;
    one_floor) #一楼
        hastochange one_floor;
        text="岳父母家哟，亲！注意点哟！！！";
        echo "one_floor" > $CURMARKFILE;
        changepiclink $OTHERPICS;
    ;;
    parents_home) #屯里父母家
        hastochange parents_home;
        text="父母家哟，亲！注意些哟！！！";
        echo "parents_home" > $CURMARKFILE;
        changepiclink $OTHERPICS;
    ;;
    auto) #自动的 也相当于是随意的
        hastochange auto;
        text="自动的哟，亲！看看自己在哪吧！";
        echo "auto" > $CURMARKFILE;
        changepiclink $OTHERPICS;
    ;;
esac
#/usr/local/bin/sl
clear
#/usr/local/bin/cowsay $text
#banner -w66 J|lolcat -a -d 1
figlet -w66 Json|lolcat -a -d 1
#fortune -s computers | cowsay -f kiss | lolcat
fortune -s computers | cowsay -f daemon | lolcat

currenthour=$(date +%H%M%S)
if [ "000000" -lt "$currenthour" ] && [ "120000" -ge "$currenthour" ]; then
    osascript -e 'say "hey Json, good morning" using "Alex"' &
elif [ "120000" -lt "$currenthour" ] && [ "190000" -ge "$currenthour" ]; then
    osascript -e 'say "hey Json, good afternoon" using "Alex"' &
elif [ "190000" -lt "$currenthour" ] && [ "240000" -ge "$currenthour" ]; then
    osascript -e 'say "hey Json, good evening" using "Alex"' &
fi
#屏幕火了
#aafire
