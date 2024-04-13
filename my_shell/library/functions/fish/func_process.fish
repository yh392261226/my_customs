function fzf_process_kill
    set pid
    set PARAMS $FZF_CUSTOM_PARAMS --bind 'focus:transform-preview-label:echo -n "[ {2} ]";' --bind 'ctrl-y:execute-silent(echo -n {2}| pbcopy)+abort' --header=(_buildFzfHeader '' 'fzf_process_kill')

    if test "$UID" != "0"
        set pid (ps -f -u $UID | sed 1d | fzf -m $PARAMS | awk '{print $2}')
    else
        set pid (ps -ef | sed 1d | fzf -m $PARAMS | awk '{print $2}')
    end

    if test "x$pid" != "x"
        echo $pid | xargs kill -{$argv[1]:-9}
    end
end
alias fpk="fzf_process_kill"

function find_process_id
    lsof -t -c $argv
end
alias fpid="find_process_id"

function fzf_process_kill2
    date
    ps -ef | fzf $FZF_CUSTOM_PARAMS \
      --bind 'focus:transform-preview-label:echo -n "[ {2} ]";' \
      --bind 'ctrl-y:execute-silent(echo -n {2}| pbcopy)+abort' \
      --bind='ctrl-r:reload(date; ps -ef)' \
      --header=(_buildFzfHeader '' 'fzf_process_kill2') \
      | awk '{print $2}' | xargs kill -9
end
alias fpk2="fzf_process_kill2"

function fzf_process_magnifier
    date
    ps -ef | fzf $FZF_CUSTOM_PARAMS \
      --bind 'focus:transform-preview-label:echo -n "[ {2} ]";' \
      --bind 'ctrl-y:execute-silent(echo -n {2}| pbcopy)+abort' \
      --bind='ctrl-r:reload(date; ps -ef)' \
      --header=(_buildFzfHeader '' 'fzf_process_magnifier') \
      | awk '{print $2}' | xargs kill -9
end
alias fpm="fzf_process_magnifier"
