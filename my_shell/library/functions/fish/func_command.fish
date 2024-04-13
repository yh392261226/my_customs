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
    --header=(_buildFzfHeader '' 'search_aliases')
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
--header=(_buildFzfHeader '' 'fzf_all_aliases') \
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
--header=(_buildFzfHeader '' 'fzf_custom_aliases'))
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
        --header=(_buildFzfHeader '' 'fzf_all_custom_functions') \
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
        --header=(_buildFzfHeader '' 'fzf_customs_functions') \
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
            --header=(_buildFzfHeader '' 'fzf_customs_fzf_awesome_functions_list'))
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
    set hasgum (ifHasCommand gum)

    if test "" = "$words"
        if test 1 = $hasgum
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
    set -l hasgum (ifHasCommand gum)

    if test "$hasgum" = "1"
        set -l choose (gum choose "1" "2")
    else
        read -l choose
    end
echo $choose
    switch "$choose"
        case "1"
            if test -f /opt/homebrew/bin/sl
                /opt/homebrew/bin/sl
            end
            if test -f /usr/local/bin/sl
                /usr/local/bin/sl
            end
        case "2"
            if test -f /usr/local/bin/lsd
                /usr/local/bin/lsd -la
            end
            if test -f /opt/homebrew/bin/lsd
                /opt/homebrew/bin/lsd -la
            end
        case "*"
            echo "无效选择，自动退出..."
    end
end
alias sl="command_sl_selector"

function fzf_man
    set batman "man {1} | col -bx | bat --language=man --plain --color always --theme=\"Monokai Extended\""
    man -k . | sort | fzf -q "$argv" --ansi --tiebreak=begin $FZF_CUSTOM_PARAMS \
        --preview-window '50%,rounded,<50(up,85%,rounded)' \
        --preview "$batman" \
        --bind 'enter:become(man {1})' \
        --bind 'ctrl-c:+change-preview(cheat {1})+change-prompt(ﯽ Cheat > )' \
        --bind 'ctrl-m:+change-preview(${batman})+change-prompt( Man > )' \
        --bind 'ctrl-r:+change-preview(tldr --color=always {1})+change-prompt(ﳁ TLDR > )' \
        --header="$(_buildFzfHeader '' 'fzf_man')"
    echo ""
end
alias fman="fzf_man"

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
        --header=(_buildFzfHeader '' 'fzf_env_vars')
end
alias fev="fzf_env_vars"

function fzf_eval_preview
    echo | fzf $FZF_CUSTOM_PARAMS --preview-window='up:90%:rounded:hidden:wrap' --preview='eval {q}' --header=(_buildFzfHeader '' 'fzf_eval_preview') --query=$argv
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
        --header=(_buildFzfHeader '' 'fzf_spell')
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
        --header=(_buildFzfHeader '' 'fzf_open_app') \
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
        --header=(_buildFzfHeader '' 'fzf_most_used_command') \
        --bind 'ctrl-y:execute-silent(echo {} | awk "{\$1=\"\";print}" | pbcopy)+abort'
end
alias fmu="fzf_most_used_command"

function fzf_manage
    set -l DIRPATH .
    if test -n "$argv[1]"; set DIRPATH $argv[1]; end

    set ACTIONCOMMAND
    if test (ifHasCommand gum) = 1
        set -l ACTIONCOMMAND 'gum confirm "确认删除?" && rm -f '
    else
        set -l ACTIONCOMMAND 'rm -f '
    end

    ls $DIRPATH | fzf $FZF_CUSTOM_PARAMS \
        --bind "ctrl-d:execute($ACTIONCOMMAND $DIRPATH/{})+reload(ls $DIRPATH || true)" \
        --bind "change:reload:sleep 0.1; ls $DIRPATH || true" \
        --bind "ctrl-o:execute-silent(open -R $DIRPATH/{})" \
        --header=(_buildFzfHeader '' 'fzf_manage') \
        --preview-window right:70%:rounded:hidden:wrap --preview " $MYRUNTIME/customs/bin/_previewer_fish $DIRPATH/{} "
end
alias fm2="fzf_manage"
