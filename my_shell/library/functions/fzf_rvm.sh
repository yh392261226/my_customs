# Desc: RVM integration
function frb() {
    local rb
    rb=$(
    (echo system; rvm list | grep ruby | cut -c 4-) |
    awk '{print $1}' |
    fzf-tmux -l 30 +m --reverse) && rvm use $rb
}