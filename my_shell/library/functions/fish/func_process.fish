function fzf_process_kill
    set pid

    if not test "(id -u)" = "0"
        set pid (ps -f -u (id -u) | sed 1d | fzf -m $FZF_CUSTOM_PARAMS --bind='focus:transform-preview-label:echo -n "[ {2} ]";' --bind='ctrl-y:execute-silent(echo -n {2}| pbcopy)+abort' --preview='echo {}' --header=(_buildFzfHeader '' 'fzf_process_kill') | awk '{print $2}')
    else
        set pid (ps -ef | sed 1d | fzf -m $FZF_CUSTOM_PARAMS --bind='focus:transform-preview-label:echo -n "[ {2} ]";' --bind='ctrl-y:execute-silent(echo -n {2}| pbcopy)+abort' --preview='echo {}' --header=(_buildFzfHeader '' 'fzf_process_kill') | awk '{print $2}')
    end

    if not test "x$pid" = "x"
        if not test "$argv[1]" = ""
            set -l para "$argv[1]"
        else
            set -l para -9
        end
        echo $pid | xargs kill -$para
    end
end
alias fpk="fzf_process_kill"

function find_process_id
    lsof -t -c $argv
end
alias fpid="find_process_id"

function fzf_process_magnifier
    ps -ef | sed 1d | fzf $FZF_CUSTOM_PARAMS \
      --bind 'focus:transform-preview-label:echo -n "[ {2} ]";' \
      --bind 'ctrl-y:execute-silent(echo -n {2}| pbcopy)+abort' \
      --bind='ctrl-r:reload(ps -ef)' \
      --header=(_buildFzfHeader '' 'fzf_process_magnifier') \
      | awk '{print $2}' | xargs kill -9
end
alias fpm="fzf_process_magnifier"
