# fzf 相关配置
eval (fzf --fish)
set -gx FZF_PREVIEW_FILE_CMD "bat --theme=gruvbox-dark --style=header,grid,numbers --color=always --pager=never"
set -gx FZF_PREVIEW_DIR_CMD "tree -C"
set -gx FZF_PREVIEW_IMG_CMD 'chafa -f iterm -s ${FZF_PREVIEW_COLUMNS}x${FZF_PREVIEW_LINES}'
set -gx FZF_DEFAULT_COMMAND "fd --exclude={.git,.idea,.vscode,.sass-cache,node_modules,build}"
set -gx TMP_FZF_HEADER_SWAP_FILE (mktemp -t tmp_fzf_header_swap.XXX)
set -gx TMP_FZF_SEARCH_SWAP_FILE (mktemp -p /tmp tmp_fzf_search_swap.XXX)
# set -gx FZF_INPUT_DISABLED 0

function _fzf_comprun
    set tmp_command $argv[1]
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
    set newheader " CTRL-H Search Infomation "
    set post_header $argv[1]
    set search_content $argv[2]

    if test -n "$post_header"
        if string match -qr '^a\+' "$post_header"
            set newheader "$newheader "(string sub -s 4 "$post_header")" "
        else if string match -qr '^r-' "$post_header"
            set newheader (string sub -s 4 "$post_header")" "
        end
    end

    if test -n "$search_content"
        set newheader "$newheader
⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊⇊
⇉ $search_content 搜索内容
⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈⇈ "
        echo $search_content > $TMP_FZF_HEADER_SWAP_FILE
    end
    echo "$newheader "
end

function _fzf_compgen_path
    fd --hidden --follow --exclude={.git,.idea,.vscode,.sass-cache} . $argv
end

function _fzf_compgen_dir
    fd --type d --hidden --follow --exclude={.git,.idea,.vscode,.sass-cache} . $argv
end

# 定义搜索过滤器
set -gx fzf_transformer_filter_all "fd --type f --type d -d 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_files "fd --type f -d 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_directories "fd --type d -d 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_hiddens "fd --type f --type d --hidden --glob '.*' "
set -gx fzf_transformer_filter_images "fd -i -t f -e jpg -e jpeg -e png -e gif --max-depth 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_medias "fd -i -t f -e mp4 -e avi -e mkv --max-depth 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_documents "fd -i -t f -e txt -e md -e log -e pdf --max-depth 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_languages "fd -e py -e js -e ts -e java -e cpp -e c -e h -e hpp -e rb -e php -e swift -e go -e rs -e sh -e bzsh -e fish -e pl -e lua -e scala -e kt -e dart -e cs -e m -e mm -e vue -e html -e htm -e css -e json -e yaml -e xml -e md -e txt -e yml -e toml -e ini -e cfg -e conf -e sql -e dockerfile -e docker-compose.yml --max-depth 3 --full-path $PWD --exclude={.git,.idea,.vscode,.sass-cache}"
set -gx fzf_transformer_filter_contents "rg --color=always --line-number --no-heading '' "

# 定义转换器
set -x fzf_transformer '
set lines (math "$FZF_LINES - $FZF_MATCH_COUNT - 1")
if test $FZF_MATCH_COUNT -eq 0
    echo "change-preview-window:hidden"
else if test $lines -gt 10
    echo "change-preview-window:right:$lines"
else if test $lines -le 3
    echo "change-preview-window:right:40"
else
    echo "change-preview-window:right:60"
end
'

set -x fzf_transformer_input_switcher '
if test $FZF_INPUT_STATE = enabled
    echo "hide-input+rebind(j,k,/)";
else if test $FZF_KEY = enter
    echo "accept";
else
    echo "abort";
end
'

set -x fzf_transformer_search_swap_type '
set -l filter_cmd
set -l label
set -l next_type

if test -f "$TMP_FZF_SEARCH_SWAP_FILE"
    set action (cat $TMP_FZF_SEARCH_SWAP_FILE)
else
    set action all
end

switch "$action"
    case all
        set filter_cmd "$fzf_transformer_filter_all"
        set label "Search All"
        set next_type files
    case files
        set filter_cmd "$fzf_transformer_filter_files"
        set label "Files Only"
        set next_type directories
    case directories
        set filter_cmd "$fzf_transformer_filter_directories"
        set label "Directories Only"
        set next_type hiddens
    case hiddens
        set filter_cmd "$fzf_transformer_filter_hiddens"
        set label "Hiddens"
        set next_type images
    case images
        set filter_cmd "$fzf_transformer_filter_images"
        set label "Images"
        set next_type medias
    case medias
        set filter_cmd "$fzf_transformer_filter_medias"
        set label "Medias"
        set next_type documents
    case documents
        set filter_cmd "$fzf_transformer_filter_documents"
        set label "Documents"
        set next_type languages
    case languages
        set filter_cmd "$fzf_transformer_filter_languages"
        set label "Languages"
        set next_type contents
    case contents
        set filter_cmd "$fzf_transformer_filter_contents"
        set label "Contents"
        set next_type all
end

echo "$next_type" > "$TMP_FZF_SEARCH_SWAP_FILE"
echo "change-list-label(╢ $label ╟)+reload($filter_cmd)"
'

# 设置 FZF 默认选项
set -gx FZF_DEFAULT_OPTS " --reverse --min-height='40' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --multi "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --style=full:double "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --cycle "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --inline-info "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --tmux "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --highlight-line "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --ansi "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --border=rounded "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --layout=reverse-list "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --padding='2' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --margin='8%' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --marker=' ✔' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --marker-multi-line='╻┃╹' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --pointer=' ↪︎' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --separator='┈┉' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --scrollbar='▌▐' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --prompt='Search  ➤ ' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --info='right' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --border-label-pos='bottom,4' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --preview-label-pos='bottom,4' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --header=' CTRL-H Search Infomation ' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --header-first "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --header-lines-border='bottom' "
# set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --no-input "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --preview-window='right:70%:border-rounded,+{2}+3/3,~3' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --walker='file,dir,hidden,follow' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --walker-skip='.git,.vscode,.idea,target,\$RECYCLE.BIN' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --preview-label='╢ Preview ╟' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --list-label '╢ Result ╟' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --list-border "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --list-label-pos=top,4 "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --header-border "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --header-label '╢ Header ╟' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --header-label-pos=top,4 "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --input-border "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --input-label '╢ Input ╟' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --input-label-pos=top,4 "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --gap "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --gap-line='"(echo '┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈' | lolcat -f -F 1.4)"' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --info-command='echo -e \"\\x1b[32;1m\$FZF_POS\\x1b[m/\$FZF_INFO Current/Matches/Total (Selected) \"' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --toggle-sort='ctrl-s' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --border-label='╢ Command ╟' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --preview '("$MYRUNTIME/customs/bin/_previewer" {}) 2> /dev/null | head -500' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='focus:transform-preview-label:echo -n \"╢ Preview: {}  ╟\";' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-/:change-preview-window(left|left,40%|left,60%|left,80%|right,40%|right,60%|right,80%|up,20%,border-horizontal|up,40%,border-horizontal|up,60%,border-horizontal|up,80%,border-horizontal|down,20%,border-horizontal|down,40%,border-horizontal|down,60%,border-horizontal|down,80%,border-horizontal|hidden|right)' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-v:change-preview-window(down,99%)' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-t:toggle-preview' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-o:become("$MYRUNTIME/customs/bin/_operator" {})' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-y:execute-silent(echo -n {} | pbcopy)+abort' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-n:page-down,ctrl-p:page-up' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-a:toggle-all' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-j:preview-down' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-k:preview-up' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-l:select-all+execute:less {+f}' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-l:+deselect-all' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='≥:next-selected,≤:prev-selected' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='shift-up:first' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='shift-down:last' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='load:change-prompt:Loaded, Search ➤ ' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-h:change-preview-label( ╢ Search Infomation ╟ )+transform-preview-label(echo \" ╢ Search Infomation ╟ \")+preview:("$MYRUNTIME/customs/bin/_previewer" \"help\")' "
# set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='ctrl-f:transform:echo $fzf_transformer_search_swap_type'"
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='resize:transform:echo $fzf_transformer'"
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='result:transform:echo $fzf_transformer'"
# set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='j:down,k:up,/:show-input+unbind(j,k,/)' "
# set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='esc:toggle-input+toggle-bind(j,k,/)+transform(if test \"$FZF_KEY\" = \"enter\"; echo accept; else; echo abort; end)' "
# set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS' --bind="esc:transform(if test \"$FZF_INPUT_STATE\" = \"enabled\"; echo \"hide-input+rebind(j,k,/)\"; else if test \"$FZF_KEY\" = \"enter\"; echo \"accept\"; else; echo \"abort\"; end)" '
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='space:change-header(╢ Type jump label ╟)+jump,jump-cancel:change-header:╢ Jump cancelled ╟' "
set FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS" --bind='focus:transform-header:file --brief {}' "

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
