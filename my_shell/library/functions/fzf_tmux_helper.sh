if [ -n "$TMUX_PANE" ]; then
    function fzf_tmux_helper() {
        local sz=$1;  shift
        local cmd=$1; shift
        tmux split-window $sz \
            "bash -c \"\$(tmux send-keys -t $TMUX_PANE \"\$(source ~/.fzf.bash; $cmd)\" $*)\""
    }
fi