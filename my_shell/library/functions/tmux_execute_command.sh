# Desc: tmux 生成一个执行 参数中的命令的临时窗口 回车后自动关闭
function tx() {
    tmux splitw "$*; echo -n Press enter to finish.; read"
    tmux select-layout tiled
    tmux last-pane
}