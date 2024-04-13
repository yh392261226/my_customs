### Package Desc: 编辑器相关命令


function editor_which
    set COMMANDBIN $argv[1]
    set FILENAME $argv[2]
    if test -f $COMMANDBIN
        if test -n "$FILENAME"
            command -v $argv > /dev/null 2>&1
            if test $status = 1
                echo "Command $argv does not exist !"
                return 1
            end
            if test -z (type $FILENAME | grep 'a shell function from') && test -z (type $FILENAME | grep 'is an alias for')
                $COMMANDBIN (which $FILENAME)
            else
                set endfile (type $FILENAME | awk '{print $NF}')
                if test -f $endfile || test -d $endfile
                    $COMMANDBIN $endfile
                else
                    editor_which $COMMANDBIN $endfile
                end
            end
        else
            $COMMANDBIN (pwd)
        end
    else
        echo "$COMMANDBIN does not exist !!!"
        return 1
    end
end
alias ew="editor_which"

function code_which
    set COMMANDBIN /usr/local/bin/code
    editor_which $COMMANDBIN $argv[1]
end
alias cw="code_which"
alias codew="code_which"

function sublime_text_which
    set COMMANDBIN $HOME/bin/subl
    editor_which $COMMANDBIN $argv[1]
end
alias sw="sublime_text_which"
alias stw="sublime_text_which"

function vim_which
    if test -f /usr/local/bin/vim
        set COMMANDBIN /usr/local/bin/vim
    elif test -f /opt/homebrew/bin/vim
        set COMMANDBIN /opt/homebrew/bin/vim
    end
    editor_which $COMMANDBIN $argv[1]
end
alias vw="vim_which"
alias viw="vim_which"

function neovim_which
    if test -f /usr/local/bin/nvim
        set COMMANDBIN /usr/local/bin/nvim
    elif test -f /opt/homebrew/bin/nvim
        set COMMANDBIN /opt/homebrew/bin/nvim
    end
    editor_which $COMMANDBIN $argv[1]
end
alias nw="neovim_which"
alias nviw="neovim_which"

function fzf_tags
    if not set -q EDITOR
        set EDITOR vim
    end

    set linen
    if test -e tags
        set linen (awk 'BEGIN { FS="\t" } !/^!/ {print toupper($4)"\t"$1"\t"$2"\t"$3}' tags | fzf $FZF_CUSTOM_PARAMS --nth=1,2 --with-nth=2 --preview-window right:50%:rounded:hidden:wrap --preview="bat {3} --color=always | tail -n +(echo {4} | tr -d \";\\\"\")" --header=(_buildFzfHeader '' 'fzf_tags'))
        $EDITOR (echo "$linen" | cut -f3) -c "set nocst" -c "silent tag (echo "$linen" | cut -f2)"
    end
end
alias ftags="fzf_tags"

function fzf_open_viminfo
    set files (grep '^>' $HOME/.viminfo | cut -c3- | while read line; if test -f (string replace -r \~ $HOME $line); echo $line; end; end | fzf-tmux $FZF_CUSTOM_PARAMS --preview='$MYRUNTIME/customs/bin/_previewer {}' --preview-window right:70%:rounded:hidden:wrap --header=(_buildFzfHeader '' 'fzf_open_viminfo') -d -m -q $argv -1)
    if test -n "$files"
        vim (string replace -r \~ $HOME $files)
    end
end
alias fov="fzf_open_viminfo"

function fzf_open_with_editor2
    set -x FZF_DEFAULT_COMMAND "fd -p -i -H -L -t f -t l -t x -E 'icloud/*' -E 'Library/*' -E 'Pictures/Photos Library.photoslibrary/*' -E '.git'"
    set -x files (fzf $FZF_CUSTOM_PARAMS --preview-window right:70%:rounded:hidden:wrap --preview 'bat --theme=timu-spacegrey --color=always {}' --header=(_buildFzfHeader '' 'fzf_open_with_editor2') --query=$argv --multi --select-1 --exit-0)
    if test -n "$files"
        vim $files
    end
end
alias fv='fzf_open_with_editor2'

function fzf_nvim
    set files (fzf $FZF_CUSTOM_PARAMS --preview-window right:70%:rounded:hidden:wrap --preview 'bat --style=numbers --line-range=:500 {}' --bind 'ctrl-o:execute(nvim {} < /dev/tty)' --header=(_buildFzfHeader '' 'fzf_nvim'))
    set count (echo "$files" | wc -l)
    if test -n "$files"
        nvim $files
    end
end
alias fnvi="fzf_nvim"
alias fnvim="fzf_nvim"

function fzf_vim
    set files (fzf $FZF_CUSTOM_PARAMS --preview-window right:70%:rounded:hidden:wrap --preview 'bat --style=numbers --line-range=:500 {}' --bind 'ctrl-o:execute(vim {} < /dev/tty)' --header=(_buildFzfHeader '' 'fzf_vim'))
    set count (echo "$files" | wc -l)
    vim $files
end
alias fvi="fzf_vim"
alias fvim="fzf_vim"

function fzf_grep_search_vim_to_line
    grep --recursive --line-number --binary-files=without-match $argv | fzf --delimiter ':' --nth 3.. $FZF_CUSTOM_PARAMS --preview-window 'right,70%,rounded,+{2}+3/3,~3' --preview 'bat --color=always {1} --highlight-line {2}' --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' --bind 'ctrl-y:execute-silent(echo -n {1}| pbcopy)+abort' --bind 'ctrl-o:execute(vim +{2} {1} < /dev/tty)' --bind 'enter:become(vim +{2} {1} < /dev/tty)' --header=(_buildFzfHeader '' 'fzf_grep_search_vim_to_line')
end
alias fgv2l="fzf_grep_search_vim_to_line"

function fzf_rg_search_vim_to_line
    rm -f /tmp/rg-fzf-r
    rm -f /tmp/rg-fzf-f

    if command -v rg &> /dev/null
        set RGBIN (command -v rg)
    else
        echo "rg not found"
        exit 1
    end

    set RG_PREFIX "$RGBIN --column --line-number --no-heading --color=always --smart-case"
    set INITIAL_QUERY (count $argv > 0; and echo $argv; or echo "")
    set -l FZF_DEFAULT_COMMAND "$RG_PREFIX (printf %q $INITIAL_QUERY)"

    fzf $FZF_CUSTOM_PARAMS \
    --ansi \
    --disabled \
    --query $INITIAL_QUERY \
    --color "hl:-1:underline,hl+:-1:underline:reverse" \
    --prompt 'ripgrep查询> ' \
    --header=(_buildFzfHeader '' 'fzf_rg_search_vim_to_line') \
    --delimiter=':' \
    --bind "start:reload:$RG_PREFIX {q};unbind(ctrl-r)" \
    --bind "change:reload:sleep 0.1; $RG_PREFIX {q} || true" \
    --bind 'ctrl-o:execute(vim +{2} {1} < /dev/tty)' \
    --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' \
    --bind 'ctrl-y:execute-silent(echo -n {1}| pbcopy)+abort' \
    --bind  "ctrl-f:unbind(change,ctrl-f)+change-prompt(fzf查询> )+enable-search+rebind(ctrl-r)+transform-query(echo {q} > /tmp/rg-fzf-r; cat /tmp/rg-fzf-f)" \
    --bind  "ctrl-r:unbind(ctrl-r)+change-prompt(ripgrep查询> )+disable-search+reload($RG_PREFIX {q} || true)+rebind(change,ctrl-f)+transform-query(echo {q} > /tmp/rg-fzf-f; cat /tmp/rg-fzf-r)" \
    --preview 'bat --color=always {1} --highlight-line {2}' \
    --preview-window 'right,70%,rounded,+{2}+3/3,~3' \
    --bind 'enter:become(vim {1} +{2})'
end
alias frv2l="fzf_rg_search_vim_to_line"

function fzf_ag_search_to_line
    set AGBIN
    if command -v rg &> /dev/null
        set AGBIN (command -v rg)
    else
        echo "rg not found"
        exit 1
    end
    set INITIAL_QUERY (count $argv > 0; and echo $argv; or echo "")
    set keywords '.'
    if test -n "$INITIAL_QUERY"
        set keywords $INITIAL_QUERY
    end
    $AGBIN --color --line-number $keywords | fzf $FZF_CUSTOM_PARAMS \
    --query $INITIAL_QUERY \
    --delimiter=':' -n 2.. \
    --preview-window 'right,70%,rounded,+{2}+3/3,~3' \
    --preview 'bat --color=always {1} --highlight-line {2}' \
    --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' \
    --bind 'ctrl-y:execute-silent(echo -n {1}| pbcopy)+abort' \
    --bind 'ctrl-o:execute(vim +{2} {1} < /dev/tty)' \
    --bind 'enter:become(vim +{2} {1} < /dev/tty)' \
    --header=(_buildFzfHeader '' 'fzf_ag_search_to_line')
end
alias fav2l="fzf_ag_search_to_line"

function fzf_rg_search_vscode_to_line
    rg --color=always --line-number --no-heading --smart-case $argv | fzf $FZF_CUSTOM_PARAMS --ansi \
    -m \
    --color="hl:-1:underline,hl+:-1:underline:reverse" \
    --delimiter=':' \
    --bind='ctrl-o:execute-silent(/usr/local/bin/code --new-window --goto {1}:{2})' \
    --bind='enter:become(/usr/local/bin/code --new-window --goto {1}:{2})' \
    --preview='bat --color=always {1} --highlight-line {2}' \
    --preview-window='right,60%,rounded,+{2}+3/3,~3' \
    --header=(_buildFzfHeader '' 'fzf_rg_search_vscode_to_line')
end
alias frc2l='fzf_rg_search_vscode_to_line'
