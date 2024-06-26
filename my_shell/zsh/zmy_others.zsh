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
