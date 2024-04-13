### Package Desc: Docker虚拟机相关命令
### Web : docker.com

function docker_init
    [ (docker-machine status default) = 'Running' ]; or docker-machine start default
    eval (docker-machine env default)
end

function docker_stop
    docker-machine stop default
end
