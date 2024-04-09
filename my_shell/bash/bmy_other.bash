#!/usr/bin/env bash
bind -x '"\C-l":/usr/bin/clear' #清屏
#[[ -f /opt/homebrew/opt/fzf/shell/completion.bash ]] && source /opt/homebrew/opt/fzf/shell/completion.bash
[[ -f $MYRUNTIME/customs/others/fzf-tab-completion/bash/fzf-bash-completion.sh ]] && source $MYRUNTIME/customs/others/fzf-tab-completion/bash/fzf-bash-completion.sh && bind -x '"\t": fzf_bash_completion'
