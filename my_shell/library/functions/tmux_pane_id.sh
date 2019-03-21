# Desc: 打印当前tmux所有的pane id
function tping() {
    for p in $(tmux list-windows -F "#{pane_id}"); do
        tmux send-keys -t $p Enter
    done
}