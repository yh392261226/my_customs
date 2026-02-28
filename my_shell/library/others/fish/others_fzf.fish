# fzf 相关配置
eval (fzf --fish)
# ========================
# 环境变量设置
# ========================
set -gx FZF_PREVIEW_FILE_CMD "bat --theme=gruvbox-dark --style=header,grid,numbers --color=always --pager=never"
set -gx FZF_PREVIEW_DIR_CMD "tree -C"
set -gx FZF_PREVIEW_IMG_CMD 'chafa -f iterm -s ${FZF_PREVIEW_COLUMNS}x${FZF_PREVIEW_LINES}'
set -gx FZF_DEFAULT_COMMAND "fd --exclude={.git,.idea,.vscode,.sass-cache,node_modules,build}"
set -gx TMP_FZF_HEADER_SWAP_FILE /tmp/fzf_header_swap.tmp
set -gx TMP_FZF_SEARCH_SWAP_FILE /tmp/fzf_search_swap.tmp
set -gx TMP_FZF_BOOKMARKS_PATH {$HOME}/.fzf_bookmarks
if test ! -d $TMP_FZF_BOOKMARKS_PATH
    mkdir -p $TMP_FZF_BOOKMARKS_PATH
end

# ========================
# 核心函数定义
# ========================
function _fzf_comprun
    set -l tmp_command $argv[1]
    set -e argv[1]
    switch "$tmp_command"
        case cd
            fzf $argv --preview 'tree -C {} | head -200'
        case export unset
            fzf $argv --preview "eval 'echo \$'{}"
        case ssh
            fzf $argv --preview 'dig {}'
        case tree
            find . -type d | fzf --preview 'tree -C {}' $argv
        case '*'
            fzf $argv
    end
end

function _buildFzfHeader
    rm -f $TMP_FZF_HEADER_SWAP_FILE
    # 使用双引号确保换行符被解析
    set -l newheader "╭──────────────────────────────────────────────────────────────────────────────────────── -- - ･"
    set newheader "$newheader
│   CTRL-H Search Information "
    set -l post_header $argv[1]
    set -l custom_header $argv[2]

    if test -n "$post_header"
        if string match -qr '^a+' "$post_header"
            set newheader "$newheader"(string sub -s 4 -- "$post_header")" "
        else if string match -qr '^r-' "$post_header"
            set newheader (string sub -s 4 -- "$post_header")" "
        end
    end

    if test -n "$custom_header"
        # 使用双引号跨行字符串确保换行符被保留
        set newheader "$newheader
│   
│   $custom_header 搜索内容
│   "
        echo $custom_header > $TMP_FZF_HEADER_SWAP_FILE
    end
    # 确保末尾添加换行符
    set newheader "$newheader
╰──────────────────────────────────────────────────────────────────────────────────────── -- - ･"

    # 使用 printf 确保输出原始换行符
    printf "%s" "$newheader"
end

function _fzf_compgen_path
    fd --hidden --follow --exclude={.git,.idea,.vscode,.sass-cache} . "$argv"
end

function _fzf_compgen_dir
    fd --type d --hidden --follow --exclude={.git,.idea,.vscode,.sass-cache} . "$argv"
end

# ========================
# 搜索过滤器定义
# ========================
set -gx fzf_transformer_filter_all "fd --color always --type f --type d -d 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_files "fd --color always --type f -d 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_directories "fd --color always --type d -d 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_hiddens "fd --color always --type f --type d --hidden --glob '.*' "
set -gx fzf_transformer_filter_images "fd --color always -i -t f -e jpg -e jpeg -e png -e gif --max-depth 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_medias "fd --color always -i -t f -e mp4 -e avi -e mkv --max-depth 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_documents "fd --color always -i -t f -e txt -e md -e log -e pdf --max-depth 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_languages "fd --color always -e py -e js -e ts -e java -e cpp -e c -e h -e hpp -e rb -e php -e swift -e go -e rs -e sh -e bzsh -e fish -e pl -e lua -e scala -e kt -e dart -e cs -e m -e mm -e vue -e html -e htm -e css -e json -e yaml -e xml -e md -e txt -e yml -e toml -e ini -e cfg -e conf -e sql -e dockerfile -e docker-compose.yml --max-depth 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_archives "fd --color always -i -t f -e gz -e zip -e tar -e rar -e bz2 -e gzip -e 7z -e xz -e Z -e tgz -e ex --max-depth 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_contents "rg --color=always --line-number --no-heading '' "

# ========================
# FZF 转换器定义
# ========================
set -gx fzf_transformer "lines=\$(( FZF_LINES - FZF_MATCH_COUNT - 1 ))
if [[ \$FZF_MATCH_COUNT -eq 0 ]]; then
    echo \"change-preview-window:hidden\"
elif [[ \$lines -gt 10 ]]; then
    echo \"change-preview-window:\$lines\"
elif [[ \$lines -le 3 ]]; then
    echo \"change-preview-window:40\"
elif [[ \$FZF_PREVIEW_LINES -gt 0 ]]; then
    echo \"change-preview-window:40\"
fi"

set -gx fzf_transformer_input_switcher "if [[ \$FZF_INPUT_STATE = enabled ]]; then
    echo \"rebind(j,k,/)+hide-input\"
elif [[ \$FZF_KEY = enter ]]; then
    echo accept
else
    echo abort
fi"

set -gx fzf_transformer_search_swap_type "if [ -f \$TMP_FZF_SEARCH_SWAP_FILE ]; then
    local action=\$(cat \$TMP_FZF_SEARCH_SWAP_FILE)
    case \$action in
        \"all\")          echo 'files'        > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search All ╟)+reload(\$fzf_transformer_filter_all)\" ;;
        \"files\")        echo 'directories'  > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search Files Only ╟)+reload(\$fzf_transformer_filter_files)\" ;;
        \"directories\")  echo 'hiddens'      > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search Directories Only ╟)+reload(\$fzf_transformer_filter_directories)\" ;;
        \"hiddens\")      echo 'images'       > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search Hiddens ╟)+reload(\$fzf_transformer_filter_hiddens)\" ;;
        \"images\")       echo 'medias'       > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search Images Only ╟)+reload(\$fzf_transformer_filter_images)\" ;;
        \"medias\")       echo 'documents'    > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search Medias Only ╟)+reload(\$fzf_transformer_filter_medias)\" ;;
        \"documents\")    echo 'languages'    > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search Documents Only ╟)+reload(\$fzf_transformer_filter_documents)\" ;;
        \"languages\")    echo 'contents'     > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search Develop Languages Files ╟)+reload(\$fzf_transformer_filter_languages)\" ;;
        \"contents\")     echo 'archives'     > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search Contents ╟)+reload(\$fzf_transformer_filter_contents)\" ;;
        \"archives\")     echo 'all'          > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search Archives ╟)+reload(\$fzf_transformer_filter_archives)\" ;;
    esac
else
    echo \"all\" > \$TMP_FZF_SEARCH_SWAP_FILE && echo \"change-list-label(╢ Search All ╟)+reload(\$fzf_transformer_filter_all)\"
fi"

# ========================
# FZF 默认选项配置
# ========================
set -gx FZF_DEFAULT_OPTS " --min-height='40' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --multi "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --style=full:double "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --cycle "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --inline-info "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --tmux "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --highlight-line "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --ansi "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --border=rounded "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --layout=reverse "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --padding='2' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --margin='8%' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --marker=' ✔' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --marker-multi-line='╻┃╹' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --pointer=' ↪︎' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --separator='┈┉' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --scrollbar='▌▐' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --prompt='Search  ➤ ' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --info='right' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --wrap=word "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --border-label-pos='bottom,4' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --preview-label-pos='bottom,4' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --header=' CTRL-H Search Infomation ' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --header-first '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --header-lines-border='bottom' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --gutter-raw="▚"'
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --color gutter:green '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --color nomatch:dim:strip:strikethrough '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --color ghost:red:italic '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --color 'fg:underline-curly,current-fg:underline-dashed' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --no-input '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --preview-window="right:70%:border-rounded,hidden,~3" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --walker="file,dir,hidden,follow" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --walker-skip=".git,.vscode,.idea,target,\$RECYCLE.BIN" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --preview-label="╢ 预览 ╟" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --list-label "╢ 结果 ╟" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --list-border '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --list-label-pos=top,4 '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --header-border '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --header-label "╢ 页头 ╟" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --header-label-pos=top,4 '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --footer=" [ Help ] / [ Copy ] / [ Open ] " '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --footer-label "╢ 页脚 ╟" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --footer-label-pos=top,4 '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --input-border '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --input-label "╢ 过滤 ╟" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --input-label-pos=top,4 '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --gap '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --gap-line=\"$(echo '┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈' | lolcat -f -F 1.4)\"  "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --info-command="echo -e \"\\x1b[32;1m$FZF_POS\\x1b[m/$FZF_INFO Current/Matches/Total (Selected) \"" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --toggle-sort="ctrl-s" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --border-label="╢ Command ╟" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --preview "($MYRUNTIME/customs/bin/_previewer {}) 2> /dev/null | head -500" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="focus:transform-preview-label:echo -n \"╢ Preview: {}  ╟\";" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-/:change-preview-window(left|left,40%|left,60%|left,80%|right,40%|right,60%|right,80%|up,20%,border-horizontal|up,40%,border-horizontal|up,60%,border-horizontal|up,80%,border-horizontal|down,20%,border-horizontal|down,40%,border-horizontal|down,60%,border-horizontal|down,80%,border-horizontal|hidden|right)" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-v:change-preview-window(down,99%)" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-t:toggle-preview" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-o:become($MYRUNTIME/customs/bin/_operator {})" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-u:become($MYRUNTIME/customs/bin/_actioner {})" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-y:execute-silent(echo -n {} | pbcopy)+abort" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-n:page-down,ctrl-p:page-up" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-a:toggle-all" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-j:preview-down" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-k:preview-up" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-l:select-all+execute:less {+f}" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-l:+deselect-all" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind 'ctrl-f:transform:$fzf_transformer_search_swap_type'"
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="≥:next-selected,≤:prev-selected" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="shift-up:first" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="shift-down:last" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="load:change-prompt:Loaded, Search ➤ " '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="ctrl-h:change-preview-label( ╢ Search Infomation ╟ )+transform-preview-label(echo \" ╢ Search Infomation ╟ \")+preview:($MYRUNTIME/customs/bin/_previewer \"help\")" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="result:transform:$fzf_transformer" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="resize:transform:$fzf_transformer" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='j:down,k:up,/:show-input+unbind(j,k,/)' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='enter,esc,ctrl-c:transform:$fzf_transformer_input_switcher' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="space:change-header(╢ Type jump label ╟)+jump,jump-cancel:change-header:╢ Jump cancelled ╟" '
#set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="focus:transform-header:file --brief {}" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='multi:transform-footer:(( FZF_SELECT_COUNT )) && echo \"Selected \$FZF_SELECT_COUNT item(s)\"' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="click-footer:transform:(
    [[ $FZF_CLICK_FOOTER_WORD =~ Help ]] && echo \"change-preview-label( ╢ Help Infomation ╟ )+preview:(${MYRUNTIME}/customs/bin/_previewer \\\"help\\\")\"
    [[ $FZF_CLICK_FOOTER_WORD =~ Copy ]] && echo \"execute-silent(echo -n \{} | pbcopy)+abort\"
    [[ $FZF_CLICK_FOOTER_WORD =~ Open ]] && echo \"execute:open \{} \"
)" '

set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="¬:preview-half-page-down" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="˙:preview-half-page-up" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="…:preview-bottom" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="©:preview-top" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="≈:exclude-multi" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="†:toggle-track" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="÷:toggle-header" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="®:toggle-raw" '
set -gx FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS




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
