## powerline主题
#FACECODE="
#%F{green}╭─ %F{blue}$MYSYSNAME:$USERNAME @ %F{yellow}z-shell %F{green}:::๑•ิ.•ั๑::: $SYSHEADER %{$reset_color%} %F{green}
#%F{green}╰⊚ "
## 暂时弃用的图标  ⚀ ⚁ ⚂ ⚃ ⚄ ⚅
#FACECODE="%F{green}:::๑•ิ.•ั๑::: $SYSHEADER %{$reset_color%}"
#
#function powerline_precmd() {
#    # PS1="$(powerline-shell --shell zsh $?)"
#    MYPS1="$($HOME/powerline-shell.py $? --shell zsh 2> /dev/null)%F{green}"
#    export PS1="$FACECODE$MYPS1%F{yellow} ☞   "'$([ -n "$TMUX" ] && tmux setenv TMUXPWD_$(tmux display -p "#D" | tr -d %) "$PWD")'
#}
#
#function install_powerline_precmd() {
#  for s in "${precmd_functions[@]}"; do
#    if [ "$s" = "powerline_precmd" ]; then
#      return
#    fi
#  done
#  precmd_functions+=(powerline_precmd)
#}
#
#if [ "$TERM" != "linux" ]; then
#    install_powerline_precmd
#fi
#
#prompt() {
#    PS1="$(powerline-rs --shell zsh $?)"
#}
#precmd_functions+=(prompt)
