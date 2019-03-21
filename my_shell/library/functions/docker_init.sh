if [ "$PLATFORM" = 'Darwin' ]; then
    # Desc: docker初始化
    function dockerinit() {
        [ $(docker-machine status default) = 'Running' ] || docker-machine start default
        eval "$(docker-machine env default)"
    }
fi