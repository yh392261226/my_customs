#fzf 相关
set -U FZF_PREVIEW_FILE_CMD "bat"
set -U FZF_PREVIEW_DIR_CMD "tree -C"
set -U FZF_DEFAULT_COMMAND "fd --exclude={.git,.idea,.vscode,.sass-cache,node_modules,build}"
set -U FZF_DEFAULT_OPTS "--height 90% --multi --cycle --inline-info --ansi --border --layout=reverse --preview '(${MYRUNTIME}/customs/bin/mypreview {}) 2> /dev/null | head -500'  --preview-window right:70%:noborder --color 'fg:252,bg:233,hl:67,fg+:252,bg+:235,hl+:81,info:144,prompt:161,spinner:135,pointer:135,marker:118,border:254'"
set -U FZF_COMPLETION_OPTS "-1 --cycle --inline-info --ansi --height 60% --border --layout=reverse --preview '$PREVIEW {}' --preview-window 'right:70%:wrap'  $FZF_PREVIEW_KEY_BIND"
set -U FZF_TAB_OPTS (-1 --cycle --inline-info --ansi --height 90% --border --layout=reverse  --expect=/ --no-preview)
set -U FZF_TAB_OPTS (-1 --cycle --inline-info --ansi --height 90% --border --layout=reverse  --expect=/ --priview '(${MYRUNTIME}/customs/bin/mypreview {}) 2> /dev/null | head -500'  --preview-window right:70%:noborder --color 'fg:#bbccdd,fg+:#ddeeff,bg:#334455,preview-bg:#223344,border:#778899')
set -U FZF_CTRL_T_OPTS "--preview '(${MYRUNTIME}/customs/bin/mypreview {}) 2> /dev/null | head -200'"
set -U FZF_CTRL_R_OPTS "--reverse"
set -U FZF_TMUX_OPTS "-p"
function _fzf_comprun
  set command $1
  shift
    switch  "$command"
        case cd
            fzf "$@" --preview 'tree -C {} | head -200'
        case *
            fzf "$@"
    end
end
