# Desc: 
function z() {
    if [[ -z "$*" ]]; then
        cd "$(_z -l 2>&1 | fzf-tmux +s --tac | sed 's/^[0-9,.]* *//')"
    else
        _z "$@" || z
    fi
}