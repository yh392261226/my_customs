# my_customs

Usage: Add below into $HOME/.zshrc
```bash
z_config=("alias" "basic" "prompt" "export" "func" "omz" "other")
my_custom_zsh=$HOME/.runtime/customs/my_zsh

for custom_zsh_config in $z_config; do
    if [ -f $my_custom_zsh/zmy_${custom_zsh_config}.zsh ]; then
        source $my_custom_zsh/zmy_${custom_zsh_config}.zsh
    fi
done
source $z_config/zmy_changebg.zsh #background images change by bindkey of iterm2
```
