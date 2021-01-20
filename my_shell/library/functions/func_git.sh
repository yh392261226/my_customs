function fbr() { # Desc: fbr:checkout git branch
    local branches branch
    branches=$(git branch --all | grep -v HEAD) &&
        branch=$(echo "$branches" |
    fzf-tmux -d $(( 2 + $(wc -l <<< "$branches") )) +m) &&
        git checkout $(echo "$branch" | sed "s/.* //" | sed "s#remotes/[^/]*/##")
}

function fcoc() { # Desc: fcoc:checkout git commit
    local commits commit
    commits=$(git log --pretty=oneline --abbrev-commit --reverse) &&
    commit=$(echo "$commits" | fzf --tac +s +m -e) &&
    git checkout $(echo "$commit" | sed "s/ .*//")
}

function fco_preview() { # Desc: fco_preview:checkout git branch/tag, with a preview showing the commits between the tag/branch and HEAD
    local tags branches target
    tags=$(
    git tag | awk '{print "\x1b[31;1mtag\x1b[m\t" $1}') || return
    branches=$(
    git branch --all | grep -v HEAD |
    sed "s/.* //" | sed "s#remotes/[^/]*/##" |
    sort -u | awk '{print "\x1b[34;1mbranch\x1b[m\t" $1}') || return
    target=$(
    (echo "$tags"; echo "$branches") |
    fzf --no-hscroll --no-multi --delimiter="\t" -n 2 \
        --ansi --preview="git log -200 --pretty=format:%s $(echo {+2..} |  sed 's/$/../' )" ) || return
    git checkout $(echo "$target" | awk '{print $2}')
}

function fcs() { # Desc: fcs:get git commit sha. example usage: git rebase -i `fcs`
    local commits commit
    commits=$(git log --color=always --pretty=oneline --abbrev-commit --reverse) &&
    commit=$(echo "$commits" | fzf --tac +s +m -e --ansi --reverse) &&
    echo -n $(echo "$commit" | sed "s/ .*//")
}

function fco() { # Desc: fco:checkout git branch/tag
    local tags branches target
    tags=$(
    git tag | awk '{print "\x1b[31;1mtag\x1b[m\t" $1}') || return
    branches=$(
    git branch --all | grep -v HEAD             |
    sed "s/.* //"    | sed "s#remotes/[^/]*/##" |
    sort -u          | awk '{print "\x1b[34;1mbranch\x1b[m\t" $1}') || return
    target=$(
    (echo "$tags"; echo "$branches") |
    fzf-tmux -l30 -- --no-hscroll --ansi +m -d "\t" -n 2) || return
    git checkout $(echo "$target" | awk '{print $2}')
}

function fstash() { # Desc: fstash:easier way to deal with stashes. type fstash to get a list of your stashes. enter shows you the contents of the stash. ctrl-d shows a diff of the stash against your current HEAD. ctrl-b checks the stash out as a branch, for easier merging
    local out q k sha
    while out=$(
    git stash list --pretty="%C(yellow)%h %>(14)%Cgreen%cr %C(blue)%gs" |
    fzf --ansi --no-sort --query="$q" --print-query \
        --expect=ctrl-d,ctrl-b);
    do
    mapfile -t out <<< "$out"
    q="${out[0]}"
    k="${out[1]}"
    sha="${out[-1]}"
    sha="${sha%% *}"
    [[ -z "$sha" ]] && continue
    if [[ "$k" == 'ctrl-d' ]]; then
        git diff $sha
    elif [[ "$k" == 'ctrl-b' ]]; then
        git stash branch "stash-$sha" $sha
        break;
    else
        git stash show -p $sha
    fi
    done
}

function fgst() { # Desc: fgst:显示当前git版本库中未添加进版本的修改或新增文件列表
    isgit || return

    local cmd="${FZF_CTRL_T_COMMAND:-"command git status -s"}"

    eval "$cmd" | FZF_DEFAULT_OPTS="--height ${FZF_TMUX_HEIGHT:-40%} --reverse $FZF_DEFAULT_OPTS $FZF_CTRL_T_OPTS" fzf -m "$@" | while read -r item; do
    echo "$item" | awk '{print $2}'
    done
    echo
}

function fshow() { # Desc: fshow:git commit browser
git log --graph --color=always \
    --format="%C(auto)%h%d %s %C(black)%C(bold)%cr" "$@" |
fzf --ansi --no-sort --reverse --tiebreak=index --bind=ctrl-s:toggle-sort \
    --bind "ctrl-m:execute:
(grep -o '[a-f0-9]\{7\}' | head -1 |
xargs -I % sh -c 'git show --color=always % | less -R') << 'FZF-EOF'
{}"
}

function gitdiffb() { # Desc: gitdiffb:git 比对两个分支
    if [ $# -ne 2 ]; then
        echo two branch names required
        return
    fi
    git log --graph \
        --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr)%Creset' \
        --abbrev-commit --date=relative $1..$2
}

function upgitfiles() { # Desc: upgitfiles:更新git的目录及git module的目录
    if [ "" != "$1" ]; then
        filepath=$1
    else
        filepath=$MYRUNTIME
    fi

    for f in $(/bin/ls $filepath/); do
        if [ -d $filepath/$f/.git ]; then
            echo $filepath/$f
            customcd $filepath/$f/ && /usr/bin/git pull
        fi
        if [ -f $filepath/$f/.gitmodules ]; then
            echo $filepath/$f
            customcd $filepath/$f/ && /usr/bin/git submodule update --init --recursive
        fi
    done
    customcd ~
}

function isgit() { # Desc: isgit:pick files from `git status -s`
    git rev-parse HEAD > /dev/null 2>&1
}

