if [ "$PLATFORM" = 'Darwin' ]; then
    # Desc: 图片压缩
    function resizes() {
        mkdir -p out &&
        for jpg in *.JPG; do
            echo $jpg
            [ -e out/$jpg ] || sips -Z 2048 --setProperty formatOptions 80 $jpg --out out/$jpg
        done
    }
fi