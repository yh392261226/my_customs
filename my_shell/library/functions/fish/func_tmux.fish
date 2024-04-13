function tmux_configs_select
    set CONFIGS $MYRUNTIME/tmuxconfigs  # 配置文件地址
    set EXT tmux.conf

    if test -d $CONFIGS
        set configs (ls $CONFIGS/*$EXT)
        if test (count $configs) -ne 0
            echo "Input the NO. :"
            set posit 0
            for file in $configs
                echo $posit "：" (basename $file | awk -F ".$EXT" '{print $1}')
                set posit (math $posit + 1)
            end
            read conf
            if test $conf -lt (count $configs)
                tmux -f $configs[$conf]
                return 0
            else
                echo "The config you choose does not exists ！！！"
                return 1
            end
        else
            echo "No config can be found ！！！"
            return 1
        end
    else
        echo "Path of config does not exists ！！！"
        return 1
    end
end
alias tcs="tmux_configs_select"

function fzf_tmux_pane
    set panes (tmux list-panes -s -F '#I:#P - #{pane_current_path} #{pane_current_command}')
    set current_pane (tmux display-message -p '#I:#P')
    set current_window (tmux display-message -p '#I')

    set target (echo "$panes" | grep -v "$current_pane" | fzf +m $FZF_CUSTOM_PARAMS --header=(_buildFzfHeader '' 'fzf_tmux_pane')) or return

    set target_window (echo $target | awk 'BEGIN{FS=":|-"} {print$1}')
    set target_pane (echo $target | awk 'BEGIN{FS=":|-"} {print$2]' | cut -c 1)

    if test $current_window -eq $target_window
        tmux select-pane -t {$target_window}.{$target_pane}
    else
        tmux select-pane -t {$target_window}.{$target_pane}
        tmux select-window -t $target_window
    end
end
alias ftpane="fzf_tmux_pane"

function fzf_tmux_words
    fzf_tmux_helper '-p 40' 'tmuxwords --all --scroll 500 --min 5 | fzf --multi $FZF_CUSTOM_PARAMS --header=(_buildFzfHeader '' 'fzf_tmux_words') | paste -sd" " -'
end
alias ftw="fzf_tmux_words"

function fzf_tmux_helper
    set sz $argv[1]
    set cmd $argv[2]
    tmux split-window $sz "bash -c \"(tmux send-keys -t $TMUX_PANE (source $HOME/.fzf.(nowshell); $cmd) $argv)\""
end
alias fth="fzf_tmux_helper"

function fzf_tmux_switch_session
    set session (tmux list-sessions -F "#{session_name}" | fzf-tmux $FZF_CUSTOM_PARAMS --preview='$MYRUNTIME/customs/bin/_previewer {}' --header=(_buildFzfHeader '' 'fzf_tmux_switch_session') --query=$argv[1] --select-1 --exit-0)
    if test -n $session
        tmux switch-client -t $session
    end
end
alias ftss="fzf_tmux_switch_session"

function tmux_tmp_window
    tmux splitw $argv[1]"; echo -n Press enter to finish.; read"
    tmux select-layout tiled
    tmux last-pane
end
alias ttw="tmux_tmp_window"

function tmux_list_panes
    for p in (tmux list-windows -F "#{pane_id}")
        tmux send-keys -t $p Enter
    end
end
alias tlp="tmux_list_panes"

function tmux_new_window
    if count $argv < 1
        echo 'usage: tt <commands...>'
        return 1
    end

    set head $argv[1]
    set tail 'echo -n Press enter to finish.; read'

    while count $argv > 1
        set argv[1] $argv
        tmux split-window "$SHELL -ci \"$argv[1]; $tail\""
        tmux select-layout tiled > /dev/null
    end

    tmux set-window-option synchronize-panes on > /dev/null
    $SHELL -ci "$head; $tail"
end
alias tnw="tmux_new_window"

function tmux_iris_window
    set cmd (which tmux)      # tmux path
    set session (hostname -s) # session name

    if test -z $cmd
        echo "You need to install tmux."
        return 1
    end

    $cmd has -t $session ^ /dev/null

    if test $status -ne 0
        $cmd new -d -n irc -s $session "irssi"
        $cmd neww -n zsh -t $session "zsh"
        $cmd selectw -t $session:2
    end

    $cmd att -t $session

    return 0
end
alias tiw="tmux_iris_window"

function tmux_list
    tmux ls
end
alias tl="tmux_list"

function tmux_new
    tmux new -s $argv[1]
end
alias tn="tmux_new"

function tmux_restore_last_session
    tmux a
end
alias tlasts="tmux_restore_last_session"

function tmux_recover
    tmux a -t $argv[1]
end
alias trecover="tmux_recover"

function tmux_kill
    tmux kill-session -t $argv[1]
end
alias tkill="tmux_kill"

function tmux_killall
    tmux kill-server
end
alias tkall="tmux_killall"

function tmux_windows
    tmux list-panes -a
end
alias twindows="tmux_windows"

function fzf_tm
    if test -n "$TMUX"
        set change "switch-client"
    else
        set change "attach-session"
    end
    if test -n $argv[1]
        tmux $change -t "$argv[1]" ^ /dev/null; or begin
            tmux new-session -d -s $argv[1]
            tmux $change -t "$argv[1]"
        end
        return
    end
    set session (tmux list-sessions -F "{session_name}" ^ /dev/null | fzf --exit-0 $FZF_CUSTOM_PARAMS --header=(_buildFzfHeader '' 'fzf_tm')) 
    and tmux $change -t "$session"
    or echo "No sessions found."
end
alias ftm="fzf_tm"
