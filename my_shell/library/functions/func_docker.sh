function dockerinit() { # Desc: dockerinit:docker初始化
    [ $(docker-machine status default) = 'Running' ] || docker-machine start default
    eval "$(docker-machine env default)"
}

function dockerstop() { # Desc: dockerstop:docker停止
    docker-machine stop default
}
