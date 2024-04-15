### Package Desc: Docker虚拟机相关命令
### Web : docker.com

function docker_init
    if not test (docker-machine status default) = 'Running'
        docker-machine start default
        eval "(docker-machine env default)"
    end
end

function docker_stop
    docker-machine stop default
end
