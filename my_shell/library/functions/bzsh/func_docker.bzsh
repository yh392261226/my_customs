function docker_init() { # Desc: dockerinit:docker初始化
    [ $(docker-machine status default) = 'Running' ] || docker-machine start default
    eval "$(docker-machine env default)"
}

function docker_stop() { # Desc: dockerstop:docker停止
    docker-machine stop default
}
