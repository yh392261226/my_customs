if [ "$PLATFORM" = 'Darwin' ]; then
    # Desc: docker停止
    function dockerstop() {
        docker-machine stop default
    }
fi