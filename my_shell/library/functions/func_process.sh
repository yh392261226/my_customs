function ps_kill() { # Desc: ps_kill: kill processes - list only the ones you can kill. Modified the earlier script.
    local pid
    if [ "$UID" != "0" ]; then
        pid=$(ps -f -u $UID | sed 1d | fzf -m | awk '{print $2}')
    else
        pid=$(ps -ef | sed 1d | fzf -m | awk '{print $2}')
    fi

    if [ "x$pid" != "x" ]
    then
        echo $pid | xargs kill -${1:-9}
    fi
}

#   find_pid: find out the pid of a specified process
#   -----------------------------------------------------
#       Note that the command name can be specified via a regex
#       E.g. findPid '/d$/' finds pids of all processes with names ending in 'd'
#       Without the 'sudo' it will only find processes of the current user
#   -----------------------------------------------------

function find_pid () { # Desc: find_pid:find out the pid of a specified process
    lsof -t -c "$@" ;
}

function fpid() { # Desc: find_pid:find out the pid of a specified process
    find_pid $@
}
