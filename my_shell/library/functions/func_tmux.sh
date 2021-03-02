function tmuxf() { # Desc: tmuxf:tmux 根据选择使用配置文件
    local CONFIGS=$MYRUNTIME/tmuxconfigs  #配置文件地址
    local EXT=tmux.conf

    if [ -d $CONFIGS ]; then
        local configs=($(ls $CONFIGS/*${EXT}))
        if [ "${#configs[*]}" != "0" ]; then
            echo "Input the NO. :";
            local posit=0
            for file in ${configs[*]}; do
                echo $posit "：" $(basename ${file} | awk -F ".$EXT" '{print $1}');
                ((posit+=1))
            done
            #echo ${configs[2]}
            read conf
            if [ "$conf" -lt "${#configs[*]}" ]; then
                tmux -f ${configs[$conf]}
                return 0
            else
                echo "The config you choose does not exists ！！！";
                return 1
            fi
        else
            echo "No config can be found ！！！";
            return 1
        fi
    else
        echo "Path of config does not exists ！！！";
        return 1
    fi
}

function ftpane() { # Desc: ftpane:tmux switch pane (@george-b)
    local panes current_window current_pane target target_window target_pane
    panes=$(tmux list-panes -s -F '#I:#P - #{pane_current_path} #{pane_current_command}')
    current_pane=$(tmux display-message -p '#I:#P')
    current_window=$(tmux display-message -p '#I')

    target=$(echo "$panes" | grep -v "$current_pane" | fzf +m --reverse) || return

    target_window=$(echo $target | awk 'BEGIN{FS=":|-"} {print$1}')
    target_pane=$(echo $target | awk 'BEGIN{FS=":|-"} {print$2}' | cut -c 1)

    if [[ $current_window -eq $target_window ]]; then
        tmux select-pane -t ${target_window}.${target_pane}
    else
        tmux select-pane -t ${target_window}.${target_pane} &&
            tmux select-window -t $target_window
    fi
}

function fzf_tmux_words() { # Desc: fzf_tmux_words:tmux中 https://github.com/wellle/tmux-complete.vim  Bind CTRL-X-CTRL-T to tmuxwords.sh #bind '"\C-x\C-t": "$(fzf_tmux_words)\e\C-e"'
    fzf_tmux_helper \
        '-p 40' \
        'tmuxwords --all --scroll 500 --min 5 | fzf --multi | paste -sd" " -'
}

function fzf_tmux_helper() { # Desc: fzf_tmux_helper:tmux中利用fzf的帮助
    local sz=$1;  shift
    local cmd=$1; shift
    tmux split-window $sz \
        "bash -c \"\$(tmux send-keys -t $TMUX_PANE \"\$(source ~/.fzf.bash; $cmd)\" $*)\""
}

function fs() { # Desc: fs:Switch tmux-sessions
    local session
    session=$(tmux list-sessions -F "#{session_name}" | \
        fzf-tmux --query="$1" --select-1 --exit-0) &&
        tmux switch-client -t "$session"
}

function tx() { # Desc: tx:tmux 生成一个执行 参数中的命令的临时窗口 回车后自动关闭
    tmux splitw "$*; echo -n Press enter to finish.; read"
    tmux select-layout tiled
    tmux last-pane
}

function tping() { # Desc: tping:打印当前tmux所有的pane id
    for p in $(tmux list-windows -F "#{pane_id}"); do
        tmux send-keys -t $p Enter
    done
}

function tt() { # Desc: tt:tmux 中自动起一个窗口去做操作
    if [ $# -lt 1 ]; then
        echo 'usage: tt <commands...>'
        return 1
    fi

    local head="$1"
    local tail='echo -n Press enter to finish.; read'

    while [ $# -gt 1 ]; do
        shift
        tmux split-window "$SHELL -ci \"$1; $tail\""
        tmux select-layout tiled > /dev/null
    done

    tmux set-window-option synchronize-panes on > /dev/null
    $SHELL -ci "$head; $tail"
}

function tmuxen() { # Desc: tmuxen:tmuxen 启动tmux iris聊天窗口模式
    #
    # name     : tmuxen, tmux environment made easy
    # author   : Xu Xiaodong <xxdlhy@gmail.com>
    # license  : GPL
    # created  : 2012 Jul 01
    # modified : 2016 Nov 12
    #

    cmd=$(which tmux)      # tmux path
    session=$(hostname -s) # session name

    if [ -z $cmd ]; then
        echo "You need to install tmux."
        exit 1
    fi

    $cmd has -t $session 2> /dev/null

    if [ $? -ne 0 ]; then
        $cmd new -d -n irc -s $session "irssi"
        $cmd neww -n zsh -t $session "zsh"
        $cmd selectw -t $session:2
    fi

    $cmd att -t $session

    exit 0
}
