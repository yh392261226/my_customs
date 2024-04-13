#fzf 相关
eval (fzf --fish)
set -x FZF_PREVIEW_FILE_CMD "bat"
set -x FZF_PREVIEW_DIR_CMD "tree -C"
set -x FZF_PREVIEW_IMG_CMD "chafa -f iterm -s $FZF_PREVIEW_COLUMNSx$FZF_PREVIEW_LINES"
set -x FZF_DEFAULT_COMMAND "fd --exclude={.git,.idea,.vscode,.sass-cache,node_modules,build}"
set -x FZF_DEFAULT_OPTS " --min-height='40' --multi --cycle --inline-info --ansi --border=rounded --layout=reverse --padding='2' --margin='5%' --marker=' ✔' --pointer=' ↪︎' --separator='┈┉' --scrollbar='▌▐' --prompt='Search  ➤ ' --info='right' --border-label-pos='bottom,4' --preview-label-pos='bottom,4' --color 'fg:252,bg:233,hl:67,fg+:252,bg+:235,hl+:81,info:144,prompt:161,spinner:135,pointer:135,marker:118,border:254' --header=' CTRL-H Search Infomation ' --header-first"
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --preview-window="right:70%:border-rounded,+{2}+3/3,~3" --walker="file,dir,hidden,follow" --walker-skip=".git,node_modules,target,\$RECYCLE.BIN" --preview-label="╢ Search ╟" --toggle-sort="ctrl-s" --border-label="╢ Command ╟" --preview "($MYRUNTIME/customs/bin/_previewer_fish {}) 2> /dev/null | head -500" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-t:toggle-preview" --bind="focus:transform-preview-label:echo -n \"╢  {}  ╟\";" --bind="ctrl-/:change-preview-window(left|left,40%|left,60%|left,80%|right,40%|right,60%|right,80%|up,20%,border-horizontal|up,40%,border-horizontal|up,60%,border-horizontal|up,80%,border-horizontal|down,20%,border-horizontal|down,40%,border-horizontal|down,60%,border-horizontal|down,80%,border-horizontal|hidden|right)" --bind="ctrl-t:toggle-preview" --bind="ctrl-y:execute-silent(echo -n {} | pbcopy)+abort" --bind="ctrl-n:page-down,ctrl-p:page-up" --bind="ctrl-a:toggle-all" --bind="ctrl-j:preview-down" --bind="ctrl-k:preview-up" --bind="ctrl-l:select-all+execute:less {+f}" --bind="ctrl-l:+deselect-all" --bind="≥:next-selected,≤:prev-selected" --bind="shift-up:first" --bind="shift-down:last" --bind="load:change-prompt:Loaded, Search ➤" --bind="ctrl-h:change-preview-label( Search Infomation )+transform-preview-label(echo \" Search Infomation \")+preview:($MYRUNTIME/customs/bin/_previewer_fish \"help\")" '
set -x FZF_COMPLETION_OPTS "-1 --cycle --inline-info --ansi  --border='bottom' --layout='reverse' --preview '$MYRUNTIME/customs/bin/_previewer_fish {}' --preview-window 'right:70%:wrap'  $FZF_PREVIEW_KEY_BIND"
set -x FZF_TAB_OPTS "-1 --cycle --inline-info --ansi  --border='bottom' --layout='reverse'  --expect='/' --priview='($MYRUNTIME/customs/bin/_previewer_fish {}) 2> /dev/null | head -500'  --preview-window='right:70%:border-rounded' --color='fg:#bbccdd,fg+:#ddeeff,bg:#334455,preview-bg:#223344,border:#778899'"
set -x FZF_CTRL_T_OPTS "--preview='($MYRUNTIME/customs/bin/_previewer_fish {}) 2> /dev/null | head -200'"
set -x FZF_CTRL_R_OPTS "--bind='enter:accept-or-print-query' --reverse"
set -x FZF_ALT_C_COMMAND "fd --type d . --color=never"
set -x FZF_ALT_C_OPTS "--reverse"
set -x FZF_TMUX_OPTS "-p"
set -x FZF_HELP_OPTS "--multi --layout='reverse' --preview-window='right,75%,wrap'  "
set -x FZF_HELP_OPTS $FZF_HELP_OPTS"--bind='ctrl-m:change-preview-window(down,75%,nowrap|right,75%,nowrap)'"
set -x FZF_HELP_SYNTAX "help"
set -x CLI_OPTIONS_CMD "ag -o --numbers -- \$RE"

function _fzf_comprun
    set command $argv[1]
    set argv[1]  # remove the first element

    switch $command
        case cd
            fzf $argv --preview 'tree -C {} | head -200'
        case export, unset
            fzf $argv --preview "eval 'echo \$'{}"
        case ssh
            fzf $argv --preview 'dig {}'
        case tree
            find . -type d | fzf --preview 'tree -C {}' $argv
        case '*'
            fzf $argv
    end
end

set TMP_FZF_HEADER_SWAP_FILE /tmp/tmp_fzf_header_swap

function _buildFzfHeader
    rm -f $TMP_FZF_HEADER_SWAP_FILE
    set newheader " CTRL-H Search Infomation "
    set new_header
    set post_header $argv[1]

    if test -n "$post_header"
        set newheader "$newheader $post_header"
    end

    if test -n "$argv[2]"
        set newheader "$newheader 
⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊ 
⇉ $argv[2] 搜索内容 
⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈ "
        echo $argv[2] > $TMP_FZF_HEADER_SWAP_FILE
    end
    echo "$newheader"
end

function _fzf_compgen_path
    fd --hidden --follow --exclude ".git" . $argv
end

function _fzf_compgen_dir
    fd --type d --hidden --follow --exclude ".git" . $argv
end

set fzf_transformer '
    set lines ( $FZF_LINES - $FZF_MATCH_COUNT - 1 )
    if test $FZF_MATCH_COUNT -eq 0
        echo "change-preview-window:hidden"
    else if test $lines -gt 10
        echo "change-preview-window:$lines"
    else if test $FZF_PREVIEW_LINES -ne 5
        echo "change-preview-window:10"
    end
'

# set FZF_CUSTOM_PARAMS " --reverse --multi "
