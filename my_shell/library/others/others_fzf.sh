#fzf 相关
export FZF_PREVIEW_FILE_CMD="bat"
export FZF_PREVIEW_DIR_CMD="tree -C"
export FZF_DEFAULT_COMMAND="fd --exclude={.git,.idea,.vscode,.sass-cache,node_modules,build}"
export FZF_DEFAULT_OPTS="--height 60% --multi --cycle --inline-info --ansi --border --layout=reverse --preview '(${MYRUNTIME}/customs/bin/mypreview {}) 2> /dev/null | head -500'  --preview-window right:70%:noborder --color 'fg:252,bg:233,hl:67,fg+:252,bg+:235,hl+:81,info:144,prompt:161,spinner:135,pointer:135,marker:118,border:254'"
export FZF_COMPLETION_OPTS="-1 --cycle --inline-info --ansi --height 60% --border --layout=reverse --preview '$PREVIEW {}' --preview-window 'right:70%:wrap'  $FZF_PREVIEW_KEY_BIND"
export FZF_TAB_OPTS=(-1 --cycle --inline-info --ansi --height 40% --border --layout=reverse  --expect=/ --no-preview)
export FZF_TAB_OPTS=(-1 --cycle --inline-info --ansi --height 40% --border --layout=reverse  --expect=/ --priview '(${MYRUNTIME}/customs/bin/mypreview {}) 2> /dev/null | head -500'  --preview-window right:70%:noborder --color 'fg:#bbccdd,fg+:#ddeeff,bg:#334455,preview-bg:#223344,border:#778899')
export FZF_CTRL_T_OPTS="--preview '(${MYRUNTIME}/customs/bin/mypreview {}) 2> /dev/null | head -200'"
_fzf_comprun() {
  local command=$1
  shift

  case "$command" in
    cd)           fzf "$@" --preview 'tree -C {} | head -200' ;;
    *)            fzf "$@" ;;
  esac
}