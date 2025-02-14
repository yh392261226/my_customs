[[ -f /opt/homebrew/opt/fzf/shell/completion.zsh ]] && source /opt/homebrew/opt/fzf/shell/completion.zsh

#autoload -Uz compinit
#compinit
## Completion for kitty
#kitty + complete setup zsh | source /dev/stdin

# if [ ! -d $HOME/.oh-my-zsh/custom/fzf-brew ]; then
#     git clone git@github.com:thirteen37/fzf-brew.git $HOME/.oh-my-zsh/custom/fzf-brew
# fi

[[ -f $HOME/.config/broot/launcher/bash/br ]] && source $HOME/.config/broot/launcher/bash/br

### Bashhub.com Installation
if [ -f $HOME/.bashhub/bashhub.zsh ]; then
    source $HOME/.bashhub/bashhub.zsh
fi

if command -v vfox &> /dev/null; then
    eval "$(vfox activate zsh)"
fi


_zlf() {
    emulate -L zsh
    local d=$(mktemp -d) || return 1
    {
        mkfifo -m 600 $d/fifo || return 1
        tmux split -bf zsh -c "exec {ZLE_FIFO}>$d/fifo; export ZLE_FIFO; exec lf" || return 1
        local fd
        exec {fd}<$d/fifo
        zle -Fw $fd _zlf_handler
    } always {
        rm -rf $d
    }
}
zle -N _zlf
bindkey '\ek' _zlf

_zlf_handler() {
    emulate -L zsh
    local line
    if ! read -r line <&$1; then
        zle -F $1
        exec {1}<&-
        return 1
    fi
    eval $line
    zle -R
}
zle -N _zlf_handler