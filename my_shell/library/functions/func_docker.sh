# Desc: docker初始化
function dockerinit() {
    [ $(docker-machine status default) = 'Running' ] || docker-machine start default
    eval "$(docker-machine env default)"
}

# Desc: docker停止
function dockerstop() {
    docker-machine stop default
}
