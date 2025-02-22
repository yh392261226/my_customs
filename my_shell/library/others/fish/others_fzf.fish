#fzf 相关
eval (fzf --fish)
set -gx FZF_PREVIEW_FILE_CMD "bat"
set -gx FZF_PREVIEW_DIR_CMD "tree -C"
set -gx FZF_PREVIEW_IMG_CMD "chafa -f iterm -s $FZF_PREVIEW_COLUMNSx$FZF_PREVIEW_LINES"
set -gx FZF_DEFAULT_COMMAND "fd --exclude={.git,.idea,.vscode,.sass-cache,node_modules,build}"


# 环境变量设置
set -gx TMP_FZF_HEADER_SWAP_FILE /tmp/tmp_fzf_header_swap
set -gx TMP_FZF_HEADER_SWAP_FILE (test -n "$TMPDIR"; and echo $TMPDIR; or echo /tmp)/tmp_fzf_header_swap
set -gx TMP_FZF_SEARCH_SWAP_FILE (test -n "$TMPDIR"; and echo $TMPDIR; or echo /tmp)/tmp_fzf_search_swap

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

# 构建 FZF 头部函数
function _buildFzfHeader
    rm -f $TMP_FZF_HEADER_SWAP_FILE
    set newheader " CTRL-H Search Infomation "
    set -l post_header
    set -l new_header

    test -n "$argv[1]"; and set post_header "$argv[1]"

    # 追加模式
    if string match -qr 'a+' (string sub -l 3 $post_header)
        set newheader "$newheader "(string sub -s 4 $post_header)" "
    # 替换模式
    else if string match -qr 'r-' (string sub -l 3 $post_header)
        set newheader (string sub -s 4 $post_header)" "
    end

    if test -n "$argv[2]"
        set newheader "$newheader
⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊
⇉ $argv[2] 搜索内容
⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈ "
        echo $argv[2] > $TMP_FZF_HEADER_SWAP_FILE
    end
    echo "$newheader "
end

# 过滤命令定义
set -gx fzf_transformer_filter_all "fd --type f --type d -d 3 --full-path $PWD --exclude .git --exclude .idea --exclude .vscode --exclude .sass-cache"
set -gx fzf_transformer_filter_files "fd --type f -d 3 --full-path $PWD --exclude .git --exclude .idea --exclude .vscode --exclude .sass-cache"
set -gx fzf_transformer_filter_directories "fd --type d -d 3 --full-path $PWD --exclude .git --exclude .idea --exclude .vscode --exclude .sass-cache"
set -gx fzf_transformer_filter_hiddens "fd --type f --type d --hidden --glob '.*'"
set -gx fzf_transformer_filter_images "fd -i -t f -e jpg -e jpeg -e png -e gif --max-depth 3 --full-path $PWD --exclude .git --exclude .idea --exclude .vscode --exclude .sass-cache"
set -gx fzf_transformer_filter_medias "fd -i -t f -e mp4 -e avi -e mkv --max-depth 3 --full-path $PWD --exclude .git --exclude .idea --exclude .vscode --exclude .sass-cache"
set -gx fzf_transformer_filter_documents "fd -i -t f -e txt -e md -e log -e pdf --max-depth 3 --full-path $PWD --exclude .git --exclude .idea --exclude .vscode --exclude .sass-cache"
set -gx fzf_transformer_filter_languages "fd -e py -e js -e ts -e java -e cpp -e c -e h -e hpp -e rb -e php -e swift -e go -e rs -e sh -e bzsh -e fish -e pl -e lua -e scala -e kt -e dart -e cs -e m -e mm -e vue -e html -e htm -e css -e json -e yaml -e xml -e md -e txt -e yml -e toml -e ini -e cfg -e conf -e sql -e dockerfile -e docker-compose.yml --max-depth 3 --full-path $PWD --exclude .git --exclude .idea --exclude .vscode --exclude .sass-cache"
set -gx fzf_transformer_filter_contents "rg --color=always --line-number --no-heading ''"

# 转换器定义
set -gx fzf_transformer '
    set lines (math $FZF_LINES - $FZF_MATCH_COUNT - 1)
    if test $FZF_MATCH_COUNT -eq 0
        echo "change-preview-window:hidden"
    else if test $lines -gt 10
        echo "change-preview-window:$lines"
    else if test $lines -le 3
        echo "change-preview-window:40"
    else if test $FZF_PREVIEW_LINES -gt 0
        echo "change-preview-window:40"
    end
'

set -gx fzf_transformer_input_switcher '
    if test "$FZF_INPUT_STATE" = "enabled"
        echo "rebind(j,k,/)+hide-input"
    else if test "$FZF_KEY" = "enter"
        echo accept
    else
        echo abort
    end
'

set -gx fzf_transformer_search_swap_type '
    if test -f $TMP_FZF_SEARCH_SWAP_FILE
        set action (cat $TMP_FZF_SEARCH_SWAP_FILE)
        
        switch $action
            case "all"
                echo "files" > $TMP_FZF_SEARCH_SWAP_FILE
                echo "change-list-label(╢ Search All ╟)+reload($fzf_transformer_filter_all)"
            case "files"
                echo "directories" > $TMP_FZF_SEARCH_SWAP_FILE
                echo "change-list-label(╢ Search Files Only ╟)+reload($fzf_transformer_filter_files)"
            case "directories"
                echo "hiddens" > $TMP_FZF_SEARCH_SWAP_FILE
                echo "change-list-label(╢ Search Directories Only ╟)+reload($fzf_transformer_filter_directories)"
            case "hiddens"
                echo "images" > $TMP_FZF_SEARCH_SWAP_FILE
                echo "change-list-label(╢ Search Hiddens ╟)+reload($fzf_transformer_filter_hiddens)"
            case "images"
                echo "medias" > $TMP_FZF_SEARCH_SWAP_FILE
                echo "change-list-label(╢ Search Images Only ╟)+reload($fzf_transformer_filter_images)"
            case "medias"
                echo "documents" > $TMP_FZF_SEARCH_SWAP_FILE
                echo "change-list-label(╢ Search Medias Only ╟)+reload($fzf_transformer_filter_medias)"
            case "documents"
                echo "languages" > $TMP_FZF_SEARCH_SWAP_FILE
                echo "change-list-label(╢ Search Documents Only ╟)+reload($fzf_transformer_filter_documents)"
            case "languages"
                echo "contents" > $TMP_FZF_SEARCH_SWAP_FILE
                echo "change-list-label(╢ Search Develop Languages Files ╟)+reload($fzf_transformer_filter_languages)"
            case "contents"
                echo "all" > $TMP_FZF_SEARCH_SWAP_FILE
                echo "change-list-label(╢ Search Contents ╟)+reload($fzf_transformer_filter_contents)"
        end
    else
        echo "all" > $TMP_FZF_SEARCH_SWAP_FILE
        echo "change-list-label(╢ Search All ╟)+reload($fzf_transformer_filter_all)"
    end
'

# FZF 默认设置
set -x FZF_DEFAULT_OPTS " --reverse --min-height='40' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --multi "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --style=full:double "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --cycle "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --inline-info "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --tmux "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --highlight-line "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --ansi "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --border=rounded "
# set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --layout=reverse-list "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --padding='2' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --margin='8%' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --marker=' ✔' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --marker-multi-line='╻┃╹' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --pointer=' ↪︎' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --separator='┈┉' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --scrollbar='▌▐' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --prompt='Search  ➤ ' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --info='right' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --border-label-pos='bottom,4' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --preview-label-pos='bottom,4' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --header=' CTRL-H Search Infomation ' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --header-first '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --header-lines-border='bottom' "
# set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --no-input '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --preview-window="right:70%:border-rounded,+{2}+3/3,~3" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --walker="file,dir,hidden,follow" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --walker-skip=".git,.vscode,.idea,target,\$RECYCLE.BIN" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --preview-label="╢ Preview ╟" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --list-label "╢ Result ╟" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --list-border '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --list-label-pos=top,4 '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --header-border '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --header-label "╢ Header ╟" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --header-label-pos=top,4 '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --input-border '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --input-label "╢ Input ╟" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --input-label-pos=top,4 '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --gap '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --gap-line=\"$(echo '┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈' | lolcat -f -F 1.4)\"  "
# set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --info-command='echo -e \"\\x1b[32;1m$FZF_POS\\x1b[m/$FZF_INFO Current/Matches/Total (Selected) \"' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --toggle-sort="ctrl-s" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --border-label="╢ Command ╟" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --preview "($MYRUNTIME/customs/bin/_previewer {}) 2> /dev/null | head -500" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-t:toggle-preview" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="focus:transform-preview-label:echo -n \"╢ Preview: {}  ╟\";" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-/:change-preview-window(left|left,40%|left,60%|left,80%|right,40%|right,60%|right,80%|up,20%,border-horizontal|up,40%,border-horizontal|up,60%,border-horizontal|up,80%,border-horizontal|down,20%,border-horizontal|down,40%,border-horizontal|down,60%,border-horizontal|down,80%,border-horizontal|hidden|right)" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-v:change-preview-window(down,99%)" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-t:toggle-preview" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-o:become($MYRUNTIME/customs/bin/_operator {})" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-y:execute-silent(echo -n {} | pbcopy)+abort" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-n:page-down,ctrl-p:page-up" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-a:toggle-all" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-j:preview-down" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-k:preview-up" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-l:select-all+execute:less {+f}" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-l:+deselect-all" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='result:transform: $fzf_transformer' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='resize:transform: $fzf_transformer' "
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-f:transform: $fzf_transformer_search_swap_type" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="≥:next-selected,≤:prev-selected" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="shift-up:first" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="shift-down:last" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="load:change-prompt:Loaded, Search ➤ " '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-h:change-preview-label( ╢ Search Infomation ╟ )+transform-preview-label(echo \" ╢ Search Infomation ╟ \")+preview:($MYRUNTIME/customs/bin/_previewer \"help\")" '
# set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="j:down,k:up,/:show-input+unbind(j,k,/)" '
# set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="enter,esc,ctrl-c:transform:$fzf_transformer_input_switcher" '
set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="space:change-header(╢ Type jump label ╟)+jump,jump-cancel:change-header:╢ Jump cancelled ╟" '
#set -x FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="focus:transform-header:file --brief {}" '





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
