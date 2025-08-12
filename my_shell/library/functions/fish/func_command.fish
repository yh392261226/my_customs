### Package Desc: 自定义命令


function search_aliases
    set MYRUNTIME (cat $HOME/.myruntime)
    set -l current_dir (pwd)
    cd $MYRUNTIME/customs/my_shell/library/functions/fish
    set -l Content_command
    set -l tmp_fzf_default_command "$FZF_DEFAULT_COMMAND"
    if test -n "$argv"
        set FZF_DEFAULT_COMMAND "find . -name '*.fish' | xargs grep $argv | awk -F':' '{print $1}' | sed 's/\.\///g' | sort | uniq"
    else
        set FZF_DEFAULT_COMMAND "find . -name '*.fish' | sed 's/\.\///g' | sort | uniq"
    end

    fzf --no-sort \
    --tac \
    $FZF_CUSTOM_PARAMS \
    --preview-window right:70%:rounded:hidden:wrap \
    --delimiter=':' \
    --preview 'bat --theme=gruvbox-dark --color=always --style=header,grid,numbers {1}' \
    --header="$(_buildFzfHeader '' 'search_aliases')"
    cd $current_dir
    set FZF_DEFAULT_COMMAND "$tmp_fzf_default_command"
end
alias sas="search_aliases"

function fzf_all_aliases
    set -l TMP_ALIASES_FILE (mktemp)
    alias | sed -e "s/^alias //g" > $TMP_ALIASES_FILE
    if test -f $TMP_ALIASES_FILE
        eval (cat $TMP_ALIASES_FILE | awk -F' ' '{print $1}' | sed -e "s/^[ ]*//g" | grep -v -E "^--(.*?)" | fzf $FZF_CUSTOM_PARAMS \
--preview-window right:70%:rounded:hidden:wrap \
--preview "$MYRUNTIME/customs/bin/_show_custom_alias {} $TMP_ALIASES_FILE"  \
--header="$(_buildFzfHeader '' 'fzf_all_aliases')" \
--bind "ctrl-o:execute(bat --theme=gruvbox-dark --color=always --style=header,grid,numbers $TMP_ALIASES_FILE > /dev/tty)")
        rm -f $TMP_ALIASES_FILE
    end
end
alias faa="fzf_all_aliases"

function fzf_custom_aliases
    set -l TMP_ALIASES_FILE (mktemp)

    find $MYRUNTIME/customs/my_shell/* -type f -name "*.fish" ! -path "$MYRUNTIME/customs/my_shell/nu/*" ! -path "$MYRUNTIME/customs/my_shell/bzsh/*" ! -path "$MYRUNTIME/customs/my_shell/library/functions/bzsh/*" | xargs grep -rE '^alias\ ' > $TMP_ALIASES_FILE
    if test -f $TMP_ALIASES_FILE
        eval (cat $TMP_ALIASES_FILE | awk '{print $2}' | sed "s/'//g" | sed 's/"//g' | awk -F'=' '{print $1}' | fzf --no-sort --tac $FZF_CUSTOM_PARAMS \
--preview-window right:70%:rounded:nohidden:wrap \
--preview "$MYRUNTIME/customs/bin/_show_custom_alias {} $TMP_ALIASES_FILE \"customs\""  \
--bind 'focus:transform-preview-label:echo -n "[ {} ]";' \
--bind "ctrl-o:execute(bat --theme=gruvbox-dark --color=always --style=header,grid,numbers $TMP_ALIASES_FILE > /dev/tty)" \
--header="$(_buildFzfHeader '' 'fzf_custom_aliases')")
        rm -f $TMP_ALIASES_FILE
    end
end
alias fca="fzf_custom_aliases"

function custom_aliases_from_a2z
    hr "⬳"
    echo "[ "(echo -e (printf '\\\x%x\n' (seq 97 122)))" ]"
    hr "⬳"
    echo "⭆ Already exists command:"
    hr "⬳"
    for word in a b c d e f g h i j k l m n o p q r s t u v w x y z
        hr "↼"
        type $word
        hr "↼"
    end
end
alias a2z="custom_aliases_from_a2z"

function fzf_all_custom_functions
    set -l TMP_ALL_FUNCTIONS_FILE (mktemp)
    functions > $TMP_ALL_FUNCTIONS_FILE
    if test -f $TMP_ALL_FUNCTIONS_FILE
        set selected (cat $TMP_ALL_FUNCTIONS_FILE | fzf $FZF_CUSTOM_PARAMS +m \
        --preview-window right:70%:rounded:hidden:wrap \
        --preview "$MYRUNTIME/customs/bin/_show_awesome_function {} $TMP_ALL_FUNCTIONS_FILE 'functions' 'fish'" \
        --header="$(_buildFzfHeader '' 'fzf_all_custom_functions')" \
        --bind="ctrl-y:execute-silent($MYRUNTIME/customs/bin/_show_awesome_function {} $TMP_ALL_FUNCTIONS_FILE 'functions' 'fish'| pbcopy)+abort")
        if test -n "$selected"
            eval "$selected"
        end
        rm -f $TMP_ALL_FUNCTIONS_FILE
    end
end
alias faf="fzf_all_custom_functions"

function fzf_customs_functions
    set -l TMP_FUNCTIONS_FILE (mktemp)
    find $MYRUNTIME/customs/my_shell/library/functions/ -type f -name "*bzsh" | xargs grep -E "(function )(.*?)[^(]*.*#.*Desc" | grep -v '$MYRUNTIME' > $TMP_FUNCTIONS_FILE
    if test -f $TMP_FUNCTIONS_FILE
        eval (cat $TMP_FUNCTIONS_FILE | awk '{$1=""; print $0 }' | \
        sed 's/^[[:blank:]]\{1,\}//' | \
        sed -e "s/() {//" | awk -F'#' '{print $1}' | \
        grep -E "(.*?)[^(]*" | \
        sed -e 's/ $//g' | \
        fzf $FZF_CUSTOM_PARAMS \
        --preview-window right:70%:rounded:hidden:wrap \
        --preview "$MYRUNTIME/customs/bin/_show_awesome_function {} $TMP_FUNCTIONS_FILE 'fish'" \
        --header="$(_buildFzfHeader '' 'fzf_customs_functions')" \
        --bind "ctrl-o:execute(bat $TMP_FUNCTIONS_FILE > /dev/tty)")
        rm -f $TMP_FUNCTIONS_FILE
    end
end
alias fcf="fzf_customs_functions"

function fzf_customs_fzf_awesome_functions_list
    if not test -f $HOME/.myruntime
        echo "Awesome Fzf Functions Location Not Found !"
    else
        set -l AWESOME_FZF_FUNCTIONS_LOCATION (cat $HOME/.myruntime)/customs/my_shell/
        set -l TMP_FZF_FUNCTIONS_FILE (mktemp)
        find $AWESOME_FZF_FUNCTIONS_LOCATION -type f -name "*fish" | xargs grep -E "(function fzf_)(.*?)[^(]*" > $TMP_FZF_FUNCTIONS_FILE
        if not test -f $TMP_FZF_FUNCTIONS_FILE
            echo "Awesome Fzf Functions Collection File Does Not Exist !"
        else
            eval (cat $TMP_FZF_FUNCTIONS_FILE | \
            awk '{$1=""; print $0 }' | \
            sed 's/^[[:blank:]]\{1,\}//' | sed -e "s/() {//" | \
            awk -F'#' '{print $1}' | \
            grep -E "(^fzf_)(.*?)[^(]*" | \
            sed -e 's/ $//g' | \
            fzf $FZF_CUSTOM_PARAMS \
            --preview "$MYRUNTIME/customs/bin/_show_awesome_function {} $TMP_FZF_FUNCTIONS_FILE 'fish'" \
            --preview-window right:70%:rounded:hidden:wrap \
            --bind "ctrl-o:execute(bat $TMP_FZF_FUNCTIONS_FILE > /dev/tty)" \
            --header="$(_buildFzfHeader '' 'fzf_customs_fzf_awesome_functions_list')")
            rm -f $TMP_FZF_FUNCTIONS_FILE
        end
    end
end
alias fff="fzf_customs_fzf_awesome_functions_list"

function update_iterm2_shell_integration
    curl -L https://iterm2.com/shell_integration/install_shell_integration_and_utilities.sh | bash
end
alias upisi="update_iterm2_shell_integration"

function show_bad_links
    set -l readpath $HOME
    if test -n $argv[1]
        set -l readpath $argv[1]
    end
    echo "File List broken links:"
    for file in (ls -a $readpath)
        set realpath (/usr/bin/readlink $readpath/$file)
        if not test -f $realpath; and not test -d $realpath
            echo $readpath/$file
        end
    end
end
alias badlinks="show_bad_links"

function build_by_extension
    if test (count $argv) -eq 0
        return
    end

    set -l cmd "find (pwd)"
    for ext in $argv
        set -l cmd " $cmd -name '*.$ext' -o"
    end
    echo (string sub -s 0 -l (math (string length $cmd) - 3) $cmd) > cscope.files; and cscope -b -q; and rm cscope.files
end
alias csbuild="build_by_extension"

function clear_camera_cache
    sudo killall VDCAssistant
end
alias ccamera="clear_camera_cache"

function sign_tnt_code_name
    if test (count $argv) -ne 1
        echo "Type $argv[1] App path to replace the app sign"
        return 1
    end
    if test -d $argv[1]
        /usr/bin/codesign --force --deep --sign - $argv[1]
    else
        echo "The app path does not exists !!!"
        return 1
    end
end
alias cs="sign_tnt_code_name"
alias stnt="sign_tnt_code_name"

function speaking_by_osx_voice
    set words $argv
    if test "" = "$words"
        if command -q gum
            gum input --placeholder "Type something..."
        else
            echo "请输入要说的话 \n例如：$argv[1] haha "
            return 1
        end
    end
    osascript -e 'say "$words" using "Ting-Ting"'
end
alias sbov="speaking_by_osx_voice"

function my_weather
    if test -f /opt/homebrew/opt/curl/bin/curl
        /opt/homebrew/opt/curl/bin/curl https://wttr.in/harbin\?lang\=zh
    else
        curl https://wttr.in/harbin\?lang\=zh
    end
end
alias myweather="my_weather"

function history_sort_by_used
    set -l last_command_type (history | tail -n 1 | awk '{print($0~/^[-]?([0-9])+[.]?([0-9])+$/)?"number":"string"}')
    if test "$last_command_type" = "number"
        history | awk '{$1="";print}' | sort -rn | uniq -c | sort -rn | less
    else
        history | sort -rn | uniq -c | sort -rn | less
    end
end
alias hsu="history_sort_by_used"

function fzf_history_repeat
    eval ( history | fzf +s --tac $FZF_CUSTOM_PARAMS \
--preview ' echo {} | awk "{\$1=\"\";print}"' \
--bind 'focus:transform-preview-label:echo -n "[ {1} ]";' \
--bind 'ctrl-y:execute-silent(echo {} | awk "{\$1=\"\";print}" | pbcopy)+abort' \
--header="$(_buildFzfHeader '' 'fzf_aliases')" \
     | sed 's/ *[0-9]* *//')
end
alias fhr="fzf_history_repeat"

function help_by_tldr
    tldr $argv
end
alias help="help_by_tldr"

function ps_or_procs_search
    if test "" = "$argv"
        return 1
    end
    if command -v procs &> /dev/null
        procs | grep "$argv" | grep -v grep 
    else
        ps -ef|grep "$argv" | grep -v grep #|fzf
    end
end
alias p='ps_or_procs_search'

function btop
    if test -f /usr/local/bin/bashtop
        /usr/local/bin/bashtop $argv
    else
        echo "bashtop does not exists !"
    end
end
alias bt="btop"

function fzf_history
    history | fzf $FZF_CUSTOM_PARAMS \
--preview ' echo {}' \
--bind 'focus:transform-preview-label:echo -n "[ {} ]";' \
--header="$(_buildFzfHeader '' 'fzf_history')" \
--bind 'ctrl-y:execute-silent(echo {} | pbcopy)+abort'
end
alias fh="fzf_history"

function file_tree
    set -l mpath './'
    if test -n "$argv"
        set -l mpath $argv[1]
    end
    ls -R $mpath | grep ":" | sed -e 's/://' -e 's/[^-][^\/]*\//--/g' -e 's/^/ /' -e 's/-/|/'
end
alias ftree="file_tree"

function fzf_history_print
    set -l cmd (history | fzf +s --tac $FZF_CUSTOM_PARAMS \
        --preview ' echo {} ' \
        --bind 'focus:transform-preview-label:echo -n "[ {} ]";' \
        --bind 'ctrl-y:execute-silent(echo {} | pbcopy)+abort' \
        --header="$(_buildFzfHeader '' 'fzf_history_print')" \
        | sed -E 's/ *[0-9]*\*? *//' | sed -E 's/\\/\\\\/g')
    print -z $cmd
end
alias fhp="fzf_history_print"

function command_sl_selector
    echo "执行命令行小火车：1, ls命令：2"
    
    # 检查gum是否存在
    if command -q gum
        set choose (gum choose "1" "2" | string trim)
    else
        read -p "echo '请选择: '" -l choose
        set choose (string trim "$choose")
    end
echo $choose
    switch "$choose"
        case "1"
            # 检查sl是否存在
            if test -f /opt/homebrew/bin/sl
                /opt/homebrew/bin/sl
            else if test -f /usr/local/bin/sl
                /usr/local/bin/sl
            else
                echo "未找到sl命令"
            end
            
        case "2"
            # 检查lsd是否存在
            if test -f /usr/local/bin/lsd
                /usr/local/bin/lsd -la
            else if test -f /opt/homebrew/bin/lsd
                /opt/homebrew/bin/lsd -la
            else
                echo "未找到lsd命令"
            end
            
        case '*'
            echo "无效选择，自动退出..."
    end
end
alias sl="command_sl_selector"

function tre2
    # 执行 tre 命令并生成别名文件
    command tre $argv --editor nvim
    set -l alias_file "/tmp/tre_aliases_$USER"
    
    if test -f "$alias_file"
        # 清理别名格式并选择
        set -l choose (cat $alias_file \
            | sed 's/"//g' \
            | sed "s/'//g" \
            | sed 's/^alias //g' \
            | sed 's/=eval nvim \\/=/g' \
            | sed 's/\\//g' \
            | fzf $FZF_CUSTOM_PARAMS \
                --delimiter '=' \
                --preview 'echo "AliasName:{1}\nAliasTo:{2}"' \
                --bind 'ctrl-y:execute-silent(echo -n {1} | pbcopy)+abort')
        
        if test -n "$choose"
            # 执行选中的别名
            eval (echo $choose | awk -F= '{print $1}')
        end
    end
end
alias t2="tre2"

function fzf_man
    set -l manpage "echo {} | sed 's/\\([[:alnum:][:punct:]]*\\) (\\([[:alnum:]]*\\).*/\\2 \\1/'"
    set -l batman "$manpage | xargs -r man | col -bx | bat --language=man --plain --color always --theme=\"Monokai Extended\""
    
    # 获取颜色代码
    set -l cyan (tput setaf 6)
    set -l blue (tput setaf 4)
    set -l res (tput sgr0)
    set -l bld (tput bold)

    man -k . | sort \
    | awk -v cyan="$cyan" -v blue="$blue" -v res="$res" -v bld="$bld" \
        '{ $1=cyan bld $1; $2=res blue $2; } 1' \
    | fzf \
        -q "$argv[1]" \
        --ansi \
        --tiebreak=begin \
        --prompt=' Man > ' \
        --preview-window '50%,rounded,<50(up,85%,border-bottom)' \
        --preview "$batman" \
        --bind "enter:execute($manpage | xargs -r man)" \
        --bind "ç:+change-preview(cht {1})+change-prompt(ﯽ Cheat > )" \
        --bind "µ:+change-preview($batman)+change-prompt( Man > )" \
        --bind "®:+change-preview(tldr --color=always {1})+change-prompt(ﳁ TLDR > )" \
        --header="$(_buildFzfHeader '' 'fzf_man')"
end
alias fman="fzf_man"
bind -M insert \ch browser_history_manage

function mark_by_cheatsh
    if test (count $argv) -lt 1
        echo "Usage:$argv[1] language function"
        echo ""
        echo "---------------------------------------"
        echo ""
        curl cht.sh
        return 0
    end

    set url "cheat.sh/"
    if test -n "$argv[1]"
        set url "cheat.sh/$argv[1]/"
    end

    if test -n "$argv[2]"
        set url "cheat.sh/$argv[1]/$argv[2]"
    end

    if test -n "$argv[3]"
        set url "cheat.sh/$argv[1]/$argv[2]+$argv[3]"
    end

    curl $url
end
alias mbc="mark_by_cheatsh"

function fzf_env_vars
    env | fzf $FZF_CUSTOM_PARAMS \
        --bind 'ctrl-k:execute-silent(echo {1} | pbcopy)+abort' \
        --bind 'ctrl-v:execute-silent(echo {2} | pbcopy)+abort' \
        --bind 'focus:transform-preview-label:echo [ {1} ]' \
        --delimiter='=' \
        --preview='echo {2}' \
        --header="$(_buildFzfHeader '' 'fzf_env_vars')"
end
alias fev="fzf_env_vars"

function fzf_eval_preview
    echo | fzf $FZF_CUSTOM_PARAMS --preview-window='up:90%:rounded:hidden:wrap' --preview='eval {q}' --header="$(_buildFzfHeader '' 'fzf_eval_preview')" --query=$argv
end
alias fep="fzf_eval_preview"

function fold
    if test (count $argv) -eq 0
        /usr/bin/fold -w $COLUMNS -s
    else
        /usr/bin/fold $argv
    end
end

function fzf_spell
    cat /usr/share/dict/words | fzf $FZF_CUSTOM_PARAMS \
        --preview-window up:70%:rounded:hidden:wrap \
        --preview 'wn {} -over | fold' \
        --header="$(_buildFzfHeader '' 'fzf_spell')"
end
alias fspell="fzf_spell"

function dic
    if test (count $argv) -eq 0
        wn (fzf_spell) -over | fold
    else
        wn $argv -over | fold
    end
end

function last_theme
    # Desc: function: last_theme: 获取theme命令最后一次的设置
    echo ($MYRUNTIME/customs/bin/theme -l|tail -n2|head -n1)
end
alias ltheme="last_theme"

function fzf_open_app
    # Desc: function: fzf_open_app: 利用fzf通过终端打开App
    ls /Applications/ | fzf --ansi $FZF_CUSTOM_PARAMS \
        --preview-window right:70%:rounded:hidden:wrap \
        --preview 'tree /Applications/{}' \
        --bind 'enter:become(open /Applications/{})' \
        --header="$(_buildFzfHeader '' 'fzf_open_app')" \
        --bind 'ctrl-y:execute-silent(echo "open /Applications/{}"| pbcopy)+abort'
end
alias foa="fzf_open_app"

function cp_forward
    cp $argv; and go2 $_
end
alias cpf="cp_forward"

function mv_forward
    mv $argv; and go2 $_
end
alias mvf="mv_forward"

function mkdir_forward
    mkdir -p $argv; cd $argv
end
alias mkf="mkdir_forward"

function fzf_most_used_command
    history | sed 's/^[[:space:]]\{0,\}[0-9]\{1,\}//g' | sed 's/^[[:space:]]*//g' | sed 's/^[[:space:]]\{0,\}[0-9]\{1,\}//g' | sed 's/^[[:space:]]*//g' | sort | uniq -c | sort -n -k1 | tail -50 | tac | fzf $FZF_CUSTOM_PARAMS --no-sort \
        --preview-window right:70%:rounded:hidden:wrap \
        --preview 'echo {} | awk "{\$1=\"\";print}"' \
        --bind 'enter:become(echo {} | awk "{\$1=\"\";print}")' \
        --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' \
        --header="$(_buildFzfHeader '' 'fzf_most_used_command')" \
        --bind 'ctrl-y:execute-silent(echo {} | awk "{\$1=\"\";print}" | pbcopy)+abort'
end
alias fmu="fzf_most_used_command"

function fzf_manage
    set -l DIRPATH .
    if test -n "$argv[1]"; set DIRPATH $argv[1]; end

    set ACTIONCOMMAND
    if command -q gum
        set -l ACTIONCOMMAND 'gum confirm "确认删除?" && rm -f '
    else
        set -l ACTIONCOMMAND 'rm -f '
    end

    ls $DIRPATH | fzf $FZF_CUSTOM_PARAMS \
        --bind "ctrl-d:execute($ACTIONCOMMAND $DIRPATH/{})+reload(ls $DIRPATH || true)" \
        --bind "change:reload:sleep 0.1; ls $DIRPATH || true" \
        --bind "ctrl-o:execute-silent(open -R $DIRPATH/{})" \
        --header="$(_buildFzfHeader '' 'fzf_manage')" \
        --preview-window right:70%:rounded:hidden:wrap --preview " $MYRUNTIME/customs/bin/_previewer_fish $DIRPATH/{} "
end
alias fm2="fzf_manage"

function fzf_search_custom_functions_by_desc
    set -l TMP_FUNCTIONS_FILE (mktemp)
    set -l COMMANDPATH "$MYRUNTIME/customs/my_shell/"
    
    find $COMMANDPATH -type f -name "*.bzsh" | xargs grep 'Desc: function:' | grep -v 'TMP_FUNCTIONS_FILE' > $TMP_FUNCTIONS_FILE
    
    if test -f $TMP_FUNCTIONS_FILE && test -n "(cat $TMP_FUNCTIONS_FILE)"
        set -l CHOOSE (cat $TMP_FUNCTIONS_FILE | awk -F'# Desc: function:' '{print $2}' | fzf $FZF_CUSTOM_PARAMS \
            --preview-window right:70%:rounded:hidden:wrap \
            --preview "echo {} | sed 's/:/\\n/g'" \
            --delimiter ':' \
            --bind "enter:become(echo {1})" \
            --bind 'ctrl-y:execute-silent(echo -n {1}| pbcopy)+abort' \
            --header="$(_buildFzfHeader '' 'fzf_search_custom_functions_by_desc')" \
            --bind "ctrl-e:execute(bat $TMP_FUNCTIONS_FILE > /dev/tty)")
        
        if test -n "$CHOOSE"
            echo $CHOOSE
            echo ""
            eval $CHOOSE
        end
        rm -f $TMP_FUNCTIONS_FILE
    end
end

alias fsf="fzf_search_custom_functions_by_desc"

function fzf_search_custom_alias_by_desc
    set -l TMP_ALIAS_FILE (mktemp)
    set -l COMMANDPATH "$MYRUNTIME/customs/my_shell/"
    
    find $COMMANDPATH -type f -name "*.bzsh" | xargs grep 'Desc: alias:' | grep -v 'TMP_ALIAS_FILE' > $TMP_ALIAS_FILE
    
    if test -f $TMP_ALIAS_FILE && test -n "(cat $TMP_ALIAS_FILE)"
        set -l CHOOSE (cat $TMP_ALIAS_FILE | awk -F'# Desc: alias:' '{print $2}' | fzf $FZF_CUSTOM_PARAMS \
            --preview-window right:70%:rounded:hidden:wrap \
            --preview "echo {} | sed 's/:/\\n/g'" \
            --delimiter ':' \
            --bind "enter:become(echo {1})" \
            --bind 'ctrl-y:execute-silent(echo -n {1}| pbcopy)+abort' \
            --header="$(_buildFzfHeader '' 'fzf_search_custom_alias_by_desc')" \
            --bind "ctrl-e:execute(bat $TMP_ALIAS_FILE > /dev/tty)")
        
        if test -n "$CHOOSE"
            echo $CHOOSE
            echo ""
            eval $CHOOSE
        end
        rm -f $TMP_ALIAS_FILE
    end
end

alias fsa="fzf_search_custom_alias_by_desc"

# 书签查看
function fzf_view_bookmarks_list
    set -l ifbreak "$argv[1]"
    if test -z "$ifbreak"
        set ifbreak 0
    end
    
    pushd "$TMP_FZF_BOOKMARKS_PATH" || return
    set -l selected (ls . | fzf $FZF_CUSTOM_PARAMS +m \
    --bind="ctrl-d:execute(rm -f $TMP_FZF_BOOKMARKS_PATH/{})+reload(ls .)" \
    --header="$(_buildFzfHeader '' 'fzf_view_bookmarks_list')" \
    --preview-window="right:70%:border-rounded,nohidden,~3" \
    --preview "($MYRUNTIME/customs/bin/_previewer $TMP_FZF_BOOKMARKS_PATH/{}) 2> /dev/null | head -500")
    popd
    
    if test -n "$selected"
        head -n 1 "$TMP_FZF_BOOKMARKS_PATH/$selected" | pbcopy
    end
    
    # if test "$ifbreak" != "0"
    #     break 2
    # end
    return 1
end
alias fvb="fzf_view_bookmarks_list"

# 获取 iTerm2 背景图片
function get_iterm2_current_background_image
    set -l bg_path (osascript -e '
tell application "iTerm"
    if current window is missing value then
        return ""
    end if
    
    tell current window
        if current session is missing value then
            return ""
        end if
        
        tell current session
            if background image is not missing value then
                return background image
            else
                return ""
            end if
        end tell
    end tell
end tell')

    if test -n "$bg_path" && test "$bg_path" != "missing value"
        echo "$bg_path"
    end
end
alias gicbg="get_iterm2_current_background_image"

function check_favo_exists
    set MYRUNTIME (cat $HOME/.myruntime)
    set RUNTIME_DIR "$MYRUNTIME/tools"
    set curmark (basename (readlink $MYRUNTIME/pictures))
    set FAVO_MARK "$RUNTIME_DIR/m_favorate_$curmark"

    # 获取当前背景图片路径
    set current_bg (get_iterm2_current_background_image)

    # 检查文件是否存在且包含指定内容
    if test -e "$FAVO_MARK" && grep -qF "$current_bg" "$FAVO_MARK"
        echo "1"
        return 1
    else
        echo "0"
        return 0
    end
end

function fzf_full_files_manager
    function ___fzf_manage_all -a Action
        # set -l TMP_FZF_SEARCH_SWAP_FILE "/tmp/fzf_search_swap"
        set -l Varname "fzf_transformer_filter_$Action"
        set -l Cmd $fzf_transformer_filter_all
        
        if set -q $Varname
            set Cmd (eval "echo \$$Varname")
        end

        echo "$Action" > $TMP_FZF_SEARCH_SWAP_FILE
        set -l Operate (eval $Cmd | fzf $FZF_CUSTOM_PARAMS +m \
            --preview "$MYRUNTIME/customs/bin/_previewer {} 2> /dev/null | head -500" \
            --header="$(_buildFzfHeader '' 'fzf_full_files_manager')")

        if test -n "$Operate"
            if [ "$Action" = "contents" ]
                set -l parts (string split ':' -- $Operate)
                set -l tmpfilepath $parts[1]
                set -l tmplinenum $parts[2]

                if command -v code > /dev/null
                    code --new-window --goto $tmpfilepath:$tmplinenum
                else if command -v nvim > /dev/null
                    nvim +$tmplinenum $tmpfilepath
                else if command -v vim > /dev/null
                    vim +$tmplinenum $tmpfilepath
                else
                    bat --highlight-line=$tmplinenum --theme=gruvbox-dark --style=full --color=always --pager=never $tmpfilepath
                end
            else
                echo $Operate
            end
        end
    end

    # while true
        # 构建菜单选项数组
        # 构建菜单选项数组
        set -l actions
        
        set -a actions \
            "🔍️ 所有文件(All)" \
            "📂 文件夹(Directory)" \
            "📄 文件(File)" \
            "🥷 隐藏文件(Hidden)" \
            "🖼️ 图片(Image)" \
            "📖 文本(Document)" \
            "📻️ 媒体(Media)" \
            "🧾 开发(Develop)" \
            "📝 全文搜索(Content)" \
            "🗜️ 压缩文件(Archive)" \
            "™️ 自定义FZF函数(Function)" \
            "®️ 自定义函数(Function)" \
            "©️ 自定义别名(Alia)" \
            "🗃️ 查看书签(BookMark)" \
            "🔚 退出系统(Exit)"
        
        # 使用 fzf 选择菜单项
        set -l action (printf "%s\n" $actions | \
            fzf +m \
                --header " 文件管理系统 " \
                --prompt "主菜单 ❯ " \
                --preview-window "up:30%" \
                --preview "echo '请选择操作类型'" \
                --height "15%" \
                --bind "space:jump,jump:accept" \
                --reverse)
        
        # 处理用户选择
        if not test -n "$action"
            return
        end
        
        switch "$action"
            case "*收藏背景图*"
                $MYRUNTIME/customs/bin/favo add
                return
                
            case "*所有文件*"
                ___fzf_manage_all "all"
                
            case "*文件夹*"
                ___fzf_manage_all "directories"
                
            case "*隐藏文件*"
                ___fzf_manage_all "hiddens"
                
            case "*压缩文件*"
                ___fzf_manage_all "archives"
                
            case "*文件*"
                ___fzf_manage_all "files"
                
            case "*图片*"
                ___fzf_manage_all "images"
                
            case "*文本*"
                ___fzf_manage_all "documents"
                
            case "*媒体*"
                ___fzf_manage_all "medias"
                
            case "*开发*"
                ___fzf_manage_all "languages"
                
            case "*全文搜索*"
                ___fzf_manage_all "contents"
                
            case "*自定义FZF函数*"
                fzf_customs_fzf_awesome_functions_list
                
            case "*自定义函数*"
                fzf_search_custom_functions_by_desc
                
            case "*自定义别名*"
                fzf_search_custom_alias_by_desc
                
            case "*查看书签*"
                fzf_view_bookmarks_list
                
            case "*退出系统*"
                return
        end
    # end
end

alias ffm="fzf_full_files_manager"
bind -M insert \cf fzf_full_files_manager

function fzf_favorate_image_manager
    set -l bg_image (get_iterm2_current_background_image)
    set -l favo_check_exists (check_favo_exists)
    # 构建菜单选项数组
    set -l actions
    if test "$TERM_PROGRAM" = "iTerm.app" && test -n "$bg_image" && test "0" = "$favo_check_exists"
        set -a actions "🗂️收藏背景图（collection）"
    end
    
    set -a actions \
        "🌐 所有收藏(All)" \
        "🔍️ 模糊搜索(Search)" \
        "📃 生成HTML相册(HTML)" \
        "🖼️ 设置指定图片为背景(Set)" \
        "🔀 随机切换背景(Random)" \
        "📍 在Finder中定位文件(Locate)" \
        "🗺️ 显示缩略图(Thumb)" \
        "🛠️ 重建收藏列表(Rebuild)" \
        "🗓️ 表格形式展示收藏(Table)" \
        "🗑️ 删除(Remove)" \
        "💡 帮助(Help)" \
        "🔚 退出系统(Exit)"
    
    # 使用 fzf 选择菜单项
    set -l action (printf "%s\n" $actions | \
        fzf +m \
            --header " 背景图收藏管理系统 " \
            --prompt "主菜单 ❯ " \
            --preview-window "up:30%" \
            --preview "echo '请选择操作类型'" \
            --height "15%" \
            --bind "space:jump,jump:accept" \
            --reverse)
    
    # 处理用户选择
    if not test -n "$action"
        return
    end
    
    switch "$action"
        case "*收藏背景图*"
            $MYRUNTIME/customs/bin/favo add
            return
        case "*所有收藏*"
            $MYRUNTIME/customs/bin/favo list
        case "*模糊搜索*"
            if command -q gum
                set text (gum choose "1" "2")
            else
                read text
            end
            
            if test "" != "$text"
                $MYRUNTIME/customs/bin/favo search "$text"
            end
        case "*生成HTML相册*"
            $MYRUNTIME/customs/bin/favo html
        case "*设置指定图片为背景*"
            if command -q gum
                set img (gum input --placeholder "Type image location")
            else
                read img
            end
            
            $MYRUNTIME/customs/bin/favo set "$img"
        case "*随机切换背景*"
            $MYRUNTIME/customs/bin/favo random
        case "*在Finder中定位文件*"
            $MYRUNTIME/customs/bin/favo locate
        case "*显示缩略图*"
            $MYRUNTIME/customs/bin/favo thumb
        case "*重建收藏列表*"
            $MYRUNTIME/customs/bin/favo rebuild
        case "*表格形式展示收藏*"
            $MYRUNTIME/customs/bin/favo table
        case "*删除*"
            $MYRUNTIME/customs/bin/favo remove
        case "*帮助*"
            $MYRUNTIME/customs/bin/favo help
        case "*退出系统*"
            return
    end
end
alias ffi="fzf_favorate_image_manager"
bind -M insert \cp fzf_favorate_image_manager

function type_whereis_command
    if not test (ifHasCommand $argv) = "1"
        echo "Command $argv does not exist !"
        return 1
    end

    if not string match -q "a function with definition" (type $argv) && not string match -q "is an alias for" (type $argv)
        type (which $argv)
    else
        set endfile (type $argv | awk '{print $NF}')
        if test -f $endfile
            type $endfile
        else
            type_whereis_command $endfile
        end
    end
end
alias typew="type_whereis_command"