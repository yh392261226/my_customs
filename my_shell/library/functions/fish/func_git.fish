function check_is_git
    git rev-parse HEAD > /dev/null 2>&1
end
alias isgit="check_is_git"

function auto_create_git_respository
    mkdir $argv[1]
    cd $argv[1]
    git init
    touch README.md
    git add README.md
    git commit -m '自动创建版本库'
    git remote add origin git@github.com:yh392261226/$argv[1].git
    git push origin master
end
alias acgr="auto_create_git_respository"

function fzf_git_checkout_branch
    set branches (git branch --all | grep -v HEAD)
    set branch (echo "$branches" | fzf-tmux $FZF_CUSTOM_PARAMS --preview='$MYRUNTIME/customs/bin/_previewer_fish {}' --header="$(_buildFzfHeader '' 'fzf_git_checkout_branch')" -d (math 2 + (count $branches)) +m)
    git checkout (echo "$branch" | sed "s/.* //" | sed "s#remotes/[^/]*/##")
end
alias fcb="fzf_git_checkout_branch"

function fzf_git_checkout_commit
    set commits (git log --pretty=oneline --abbrev-commit --reverse)
    set commit (echo "$commits" | fzf --tac +s +m -e $FZF_CUSTOM_PARAMS --preview " echo {2} " --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' --bind 'ctrl-y:execute-silent(echo -n {1}| pbcopy)+abort' --header="$(_buildFzfHeader '' 'fzf_git_checkout_commit')")
    git checkout (echo "$commit" | sed "s/ .*//")
end
alias fgcc="fzf_git_checkout_commit"

function fzf_git_checkout_preview
    set tags (git tag | awk '{print "\x1b[31;1mtag\x1b[m\t" $1}')
    [ -z "$tags" ]; and return
    set branches (git branch --all | grep -v HEAD | sed "s/.* //" | sed "s#remotes/[^/]*/##" | sort -u | awk '{print "\x1b[34;1mbranch\x1b[m\t" $1}')
    [ -z "$branches" ]; and return
    set target (echo "$tags"; echo "$branches" | fzf --no-hscroll --no-multi --delimiter="\t" -n 2 --ansi $FZF_CUSTOM_PARAMS --preview-window right:70%:rounded:hidden:wrap --preview="git log -200 --pretty=format:%s (echo {+2..} )" --bind 'focus:transform-preview-label:echo -n "[ {2} ]";' --bind 'ctrl-y:execute-silent(echo -n {2}| pbcopy)+abort' --header=(_buildFzfHeader '' 'fzf_git_checkout_preview'))
    [ -z "$target" ]; and return
    git checkout (echo "$target" | awk '{print $2}')
end
alias fgcp="fzf_git_checkout_preview"

function fzf_git_commit_sha
    set commits (git log --color=always --pretty=oneline --abbrev-commit --reverse)
    set commit (echo "$commits" | fzf --tac +s +m -e --ansi $FZF_CUSTOM_PARAMS --preview " echo {2} " --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' --bind 'ctrl-y:execute-silent(echo -n {1}| pbcopy)+abort' --header=(_buildFzfHeader '' 'fzf_git_commit_sha'))
    echo -n (echo "$commit" | sed "s/ .*//")
end
alias fgcs="fzf_git_commit_sha"

function fzf_git_checkout
    set tags (git tag | awk '{print "\x1b[31;1mtag\x1b[m\t" $1}')
    [ -z "$tags" ]; and return
    set branches (git branch --all | grep -v HEAD | sed "s/.* //" | sed "s#remotes/[^/]*/##" | sort -u | awk '{print "\x1b[34;1mbranch\x1b[m\t" $1}')
    [ -z "$branches" ]; and return
    set target (echo "$tags"; echo "$branches" | fzf-tmux $FZF_CUSTOM_PARAMS --preview='$MYRUNTIME/customs/bin/_previewer_fish {}' --header=(_buildFzfHeader '' 'fzf_git_checkout') -l30 -- --no-hscroll --ansi +m -d "\t" -n 2)
    [ -z "$target" ]; and return
    git checkout (echo "$target" | awk '{print $2}')
end
alias fgc="fzf_git_checkout"

function fzf_git_checkout2
    if test (git rev-parse --is-inside-work-tree ^ /dev/null)
        if test (count $argv) -eq 0
            set branches (git branch -a)
            set branch (begin; echo "$branches" | wc -l; end | fzf-tmux $FZF_CUSTOM_PARAMS --preview='$MYRUNTIME/customs/bin/_previewer_fish {}' --header=(_buildFzfHeader '' 'fzf_git_checkout2') -d (math 2 + (echo "$branches" | wc -l) +m))
            git checkout (echo "$branch" | sed "s/.* //" | sed "s#remotes/[^/]*/##")
        else if test (git rev-parse --verify --quiet $argv); or test (git branch --remotes | grep --extended-regexp "^[[:space:]]+origin/$argv")
            echo "Checking out to existing branch"
            git checkout $argv
        else
            echo "Creating new branch"
            git checkout -b $argv
        end
    else
        echo "Can't check out or create branch. Not in a git repo"
    end
end
alias fgc2="fzf_git_checkout2"


function fzf_git_stash
    set -l out q k sha
    while set -l out (git stash list --pretty="%C(yellow)%h %>(14)%Cgreen%cr %C(blue)%gs" | fzf $FZF_CUSTOM_PARAMS --ansi --no-sort --query="$q" --print-query --expect=ctrl-d,ctrl-b --header=(_buildFzfHeader '' 'fzf_git_stash'))
        set -l q $out[1]
        set -l k $out[2]
        set -l sha $out[-1]
        set -l sha (string split " " $sha)[1]
        if test -z $sha; continue; end
        switch $k
            case 'ctrl-d'
                git diff $sha
            case 'ctrl-b'
                git stash branch "stash-$sha" $sha
                break
            case '*'
                git stash show -p $sha
        end
    end
end
alias fgsh="fzf_git_stash"

function fzf_git_status
    if not git rev-parse --git-dir > /dev/null 2>&1
        echo "You are not in a git repository"
        return
    end
    set selected (git -c color.status=always status --short | fzf "$argv" --border -m --ansi --nth 2..,.. $FZF_CUSTOM_PARAMS --preview-window right:70%:rounded:hidden:wrap --preview '(git diff --color=always -- {-1} | sed 1,4d; cat {-1}) | head -500' --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' --bind 'ctrl-y:execute-silent(echo -n {-1}| pbcopy)+abort' --header=(_buildFzfHeader '' 'fzf_git_status') | cut -c4- | sed 's/.* -> //')
    for prog in (string split " " $selected)
        $EDITOR $prog
    end
end
alias fgs="fzf_git_status"

function fzf_git_untracked
    if not check_is_git
        return
    end

    if test -n $FZF_CTRL_T_COMMAND
        set cmd "$FZF_CTRL_T_COMMAND"
    else
        set cmd "command git status -s"
    end

    eval "$cmd" | FZF_DEFAULT_OPTS="--height ${FZF_TMUX_HEIGHT:-60%} --reverse $FZF_DEFAULT_OPTS $FZF_CTRL_T_OPTS" fzf -m "$argv" $FZF_CUSTOM_PARAMS --preview " echo {2} " --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' --bind 'ctrl-y:execute-silent(echo -n {2}| pbcopy)+abort' --header=(_buildFzfHeader '' 'fzf_git_untracked') | while read -r item; echo "$item" | awk '{print $2}'; end
    echo
end
alias fgu="fzf_git_untracked"

function fzf_git_commit_browser
    git log --graph --color=always \
        --format="%C(auto)%h%d %s %C(black)%C(bold)%cr" $argv | fzf --ansi \
        --no-sort $FZF_CUSTOM_PARAMS \
        --tiebreak=index \
        --bind 'focus:transform-preview-label:echo -n "[ {2} ]";' \
        --bind 'ctrl-y:execute-silent(echo -n {2}| pbcopy)+abort' \
        --bind "ctrl-m:execute:(grep -o '[a-f0-9]\{7\}' | head -1 | xargs -I % sh -c 'git show --color=always % | less -R') << 'FZF-EOF'
        {}" \
        --header=(_buildFzfHeader '' 'fzf_git_commit_browser')
end
alias fgcb="fzf_git_commit_browser"

function fzf_gitlog_multi
    set git_cmd 'git log --all --graph --date-order --format=format:"%C(auto)%s %d %h %C(cyan)%cd %C(bold black)%an %C(auto)" --date=short --color=always'
    set fzf_cmd 'fzf $FZF_CUSTOM_PARAMS --height 100% --multi --ansi --reverse --no-sort --tiebreak=index --header=(_buildFzfHeader "" "fzf_gitlog_multi") --preview="echo {} | grep -o \"[a-f0-9]\{7\}\" | xargs -I % sh -c \"git show % --color\"" --bind=ctrl-x:toggle-sort'

    eval $git_cmd \| $fzf_cmd | grep -o '[a-f0-9]\{7\}' | xargs -I % sh -c 'git show % --color' | cat
end
alias fgm="fzf_gitlog_multi"

function git_diff_branches
    if test (count $argv) -ne 2
        echo "two branch names required"
        return
    end

    git log --graph \
        --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr)%Creset' \
        --abbrev-commit --date=relative $argv[1]..$argv[2]
end
alias gd2b="git_diff_branches"

function update_git_files_and_modules
    set filepath $argv[1] ?? $MYRUNTIME

    for f in (/bin/ls $filepath/)
        if test -d $filepath/$f/.git
            echo $filepath/$f
            customcd $filepath/$f/; /usr/bin/git pull
        end
        if test -f $filepath/$f/.gitmodules
            echo $filepath/$f
            customcd $filepath/$f/; /usr/bin/git submodule update --init --recursive
        end
    end
    customcd ~
end
alias upgitfiles="update_git_files_and_modules"

function fzf_git_vim_to_line
    git grep --line-number . | fzf --delimiter ':' --nth 3.. $FZF_CUSTOM_PARAMS \
        --preview 'bat --color=always {1} --highlight-line {2}' \
        --bind 'focus:transform-preview-label:echo -n "[ {1} ]";' \
        --bind 'enter:become(vim {1} +{2})' \
        --bind 'ctrl-o:execute(vim +{2} {1} < /dev/tty)' \
        --bind 'ctrl-y:execute-silent(echo -n {1}| pbcopy)+abort' \
        --preview-window 'right,70%,rounded,+{2}+3/3,~3' \
        --header=(_buildFzfHeader '' 'fzf_custom_aliases')
end
alias fgitv2l="fzf_git_vim_to_line"

function fzf_git_modified_diff
    git status -s | fzf $FZF_CUSTOM_PARAMS \
        --no-sort \
        --preview 'git diff --color=always {+2} | diff-so-fancy' \
        --bind=ctrl-j:preview-down \
        --bind=ctrl-k:preview-up \
        --preview-window 'right,70%,rounded,+{2}+3/3,~3' \
        --header=(_buildFzfHeader '' 'fzf_git_modified_diff')
end
alias fgd="fzf_git_modified_diff"
