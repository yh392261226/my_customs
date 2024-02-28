[[ -f /opt/homebrew/opt/fzf/shell/completion.zsh ]] && source /opt/homebrew/opt/fzf/shell/completion.zsh

#autoload -Uz compinit
#compinit
## Completion for kitty
#kitty + complete setup zsh | source /dev/stdin

if [ ! -d $HOME/.oh-my-zsh/custom/fzf-brew ]; then
    git clone git@github.com:thirteen37/fzf-brew.git $HOME/.oh-my-zsh/custom/fzf-brew
fi

[[ -f ~/.config/broot/launcher/bash/br ]] && source ~/.config/broot/launcher/bash/br

### Bashhub.com Installation
if [ -f ~/.bashhub/bashhub.zsh ]; then
    source ~/.bashhub/bashhub.zsh
fi