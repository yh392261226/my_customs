# Desc: animated gifs from any video from Alex Sexton gist.github.com/SlexAxton/4989674
gifify () {
    if [[ -n "$1" ]]; then
        if [[ $2 == '--good' ]]; then
        ffmpeg -i "$1" -r 10 -vcodec png out-static-%05d.png
        time convert -verbose +dither -layers Optimize -resize 900x900\> out-static*.png  GIF:- | gifsicle --colors 128 --delay=5 --loop --optimize=3 - -multifile - > "$1.gif"
        rm out-static*.png
        else
        ffmpeg -i "$1" -s 600x400 -pix_fmt rgb24 -r 10 -f gif - | gifsicle --optimize=3 --delay=3 > "$1.gif"
        fi
    else
        echo "proper usage: gifify <input_movie.mov>. You DO need to include extension."
    fi
}

#Desc: cat img from url in iterm2
function imgurlcat() {
    if [ "$(env | grep 'TERM_PROGRAM=' | sed 's/TERM_PROGRAM=//')" != "iTerm.app" ]; then
        echo "This command can only be used in iterm2 !!!";
        return 0;
    fi

    if [ $# -ne 1 ]; then
        echo "Type $0 image_url"
        return 1;
    fi
    #imgurl="http://g.hiphotos.baidu.com/image/pic/item/f7246b600c338744b5a0c49b5f0fd9f9d62aa0f4.jpg"
    imgurl="$1"
    axel -U 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1 Safari/605.1.15' -q -o /tmp/$(basename  $imgurl) $imgurl

    printf '\033]1337;File=inline=1;width=30%%;preserveAspectRatio=0'
    printf ":"
    base64 < "/tmp/$(basename $imgurl)"
    printf '\a\n'

    if [ -f /tmp/$(basename $imgurl) ]; then
        rm -f /tmp/$(basename $imgurl);
    fi
}

function renamedownloadpics() {
    echo "谨慎使用， 使用前先备份，多次使用相同前缀会使你的图片文件互相覆盖导致减少y|Y（使用）n|N(不使用)"
    read line;
    if [ "$line" = "y" ] || [ "$line" = "Y" ]; then
        echo "请输入前缀"
        read prefix
    m=0
    for i in $(ls $MYRUNTIME/pictures/*(jpg|png|JPG|JPEG|Jpg|PNG|Png));
    do
        m=`expr $m + 1`
        #echo 文件名为：${i%.*}
        mv $i $MYRUNTIME/pictures/$prefix-$m.${i##*.}
    done
    echo $m
    fi
}