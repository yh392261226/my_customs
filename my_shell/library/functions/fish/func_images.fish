function gifify_from_video
    # Desc: function: gifify_from_video:Animated gifs from any video from Alex Sexton gist.github.com/SlexAxton/4989674
    if test -n "$argv"
        if test $argv[2] = '--good'
            ffmpeg -i $argv[1] -r 10 -vcodec png out-static-%05d.png
            time convert -verbose +dither -layers Optimize -resize 900x900\> out-static*.png  GIF:- | gifsicle --colors 128 --delay=5 --loop --optimize=3 - -multifile - > $argv[1].gif
            rm out-static*.png
        else
            ffmpeg -i $argv[1] -s 600x400 -pix_fmt rgb24 -r 10 -f gif - | gifsicle --optimize=3 --delay=3 > $argv[1].gif
        end
    else
        echo "proper usage: gifify <input_movie.mov>. You Do need to include extension."
    end
end
alias giffv gifify_from_video

function image_url_cat
    # Desc: function: image_url_cat:Cat img from url in iterm2
    if test (env | grep 'TERM_PROGRAM=' | sed 's/TERM_PROGRAM=//') != "iTerm.app"
        echo "This command can only be used in iterm2 !!!"
        return 0
    end

    if test (count $argv) -ne 1
        echo "Type $argv[0] image_url"
        return 1
    end
    set imgurl $argv[1]
    axel -U 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1 Safari/605.1.15' -q -o /tmp/(basename $imgurl) $imgurl

    printf '\033]1337;File=inline=1;width=30%%;preserveAspectRatio=0'
    printf ":"
    base64 < "/tmp/(basename $imgurl)"
    printf '\a\n'

    if test -f /tmp/(basename $imgurl)
        rm -f /tmp/(basename $imgurl)
    end
end
alias iuc image_url_cat

function images_rename_from_download
    # Desc: function: images_rename_from_download:重命名下载的图片
    echo "谨慎使用， 使用前先备份，多次使用相同前缀会使你的图片文件互相覆盖导致减少y|Y（使用）n|N(不使用)"
    read -P "Enter your choice: " line
    if test "$line" = "y" -o "$line" = "Y"
        echo "请输入前缀"
        read prefix
        set m 0
        for i in (ls $MYRUNTIME/pictures/*.[jpg][png][JPG][JPEG][Jpg][PNG][bmp][BMP][gif][GIF])
            set m (math $m + 1)
            mv $i $MYRUNTIME/pictures/$prefix-$m.(string match -r '\.[^.]*$' $i)
        end
        echo $m
    end
end
alias irfd images_rename_from_download

function image_resizes
    # Desc: function: image_resizes:图片压缩
    mkdir -p out
    for jpg in *.JPG
        echo $jpg
        if not test -e out/$jpg
            sips -Z 2048 --setProperty formatOptions 80 $jpg --out out/$jpg
        end
    end
end
alias ir image_resizes

function fzf_iterm2_background_image_selector
    # Desc: function: fzf_iterm2_background_image_selector: 利用fzf选择iterm2的背景图片
    set IMGPATH $MYRUNTIME/pictures
    if test "" != "$argv[1]"
        set IMGPATH $argv[1]
    end
    customcd $IMGPATH
    set selected (ls . | fzf $FZF_CUSTOM_PARAMS --preview-window right:70%:rounded:hidden:wrap --preview ' chafa -f iterm -s $FZF_PREVIEW_COLUMNSx$FZF_PREVIEW_LINES {} ' --header=(_buildFzfHeader '' 'fzf_iterm2_background_image_selector'))
    bg_change {$IMGPATH}/$selected
    customcd -
    #echo "bg_change {$IMGPATH}/$selected" | pbcopy
    #echo "Ctrl - V to paste the command, then press enter to execute."
end
alias fbg fzf_iterm2_background_image_selector
