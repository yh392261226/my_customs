# Desc: Always list directory contents upon 'cd'
function cd() { builtin cd "$@"; /bin/ls -aGH; }               # 

# Desc: Makes new Dir and jumps inside
function mcd () { mkdir -p "$1" && cd "$1"; }        # mcd:          Makes new Dir and jumps inside

# Desc: Moves a file to the MacOS trash
function trash () { command mv "$@" ~/.Trash ; }     # trash:        Moves a file to the MacOS trash

# Desc: Opens any file in MacOS Quicklook Preview
function ql () { qlmanage -p "$*" >& /dev/null; }    # ql:           Opens any file in MacOS Quicklook Preview
#   mans:   Search manpage given in agument '1' for term given in argument '2' (case insensitive)
#           displays paginated result with colored search terms and two lines surrounding each hit.             Example: mans mplayer codec
#   --------------------------------------------------------------------

# Desc: man command[$1] and highlight keyword[$2]
function mans () {
    man $1 | grep -iC2 --color=always $2 | less
}

#   showa: to remind yourself of an alias (given some part of it)
#   ------------------------------------------------------------

# Desc: 显示所有自定义命令及注释
function showa () { 
    grep --color=always -i -a2 $@ $MYRUNTIME/customs/my_shell/my_alias.sh $MYRUNTIME/customs/my_shell/my_func.sh | grep -v '^\s*$' | less -FSRXc ;
}

#   -------------------------------
#   3.  FILE AND FOLDER MANAGEMENT
#   -------------------------------

# Desc: 显示所有自定义命令及注释
function zipf () { zip -r "$1".zip "$1" ; }          # zipf:         To create a ZIP archive of a folder

#   extract:  Extract most know archives with one command
#   ---------------------------------------------------------

# Desc: 自动检测文件后缀并 自动解压
function extract () {
    if [ -f $1 ] ; then
      case $1 in
        *.tar.bz2)   tar xjf $1     ;;
        *.tar.gz)    tar xzf $1     ;;
        *.bz2)       bunzip2 $1     ;;
        *.rar)       unrar e $1     ;;
        *.gz)        gunzip $1      ;;
        *.tar)       tar xf $1      ;;
        *.tbz2)      tar xjf $1     ;;
        *.tgz)       tar xzf $1     ;;
        *.zip)       unzip $1       ;;
        *.Z)         uncompress $1  ;;
        *.7z)        7z x $1        ;;
        *)     echo "'$1' cannot be extracted via extract()" ;;
         esac
     else
         echo "'$1' is not a valid file"
     fi
}


#   ---------------------------
#   4.  SEARCHING
#   ---------------------------

# Desc: Find file under the current directory
function ff () { find . -name "$@" ; }

# Desc: Find file whose name starts with a given string
function ffs () { find . -name "$@"'*' ; }

# Desc: Find file whose name ends with a given string
function ffe () { /usr/bin/find . -name '*'"$@" ; }

# Desc: Search for a file using MacOS Spotlight's metadata
function spotlight () { mdfind "kMDItemDisplayName == '$@'wc"; }

#   ---------------------------
#   5.  PROCESS MANAGEMENT
#   ---------------------------
#   findPid: find out the pid of a specified process
#   -----------------------------------------------------
#       Note that the command name can be specified via a regex
#       E.g. findPid '/d$/' finds pids of all processes with names ending in 'd'
#       Without the 'sudo' it will only find processes of the current user
#   -----------------------------------------------------

# Desc: find out the pid of a specified process
function findPid () { lsof -t -c "$@" ; }

# Desc: List processes owned by my user:
function my_ps() { ps $@ -u $USER -o pid,%cpu,%mem,start,time,bsdtime,command ; }

# Desc: display useful host related informaton
function ii() {
    echo -e "\nYou are logged on ${RED}$HOST"
    echo -e "\nAdditionnal information:$NC " ; uname -a
    echo -e "\n${RED}Users logged on:$NC " ; w -h
    echo -e "\n${RED}Current date :$NC " ; date
    echo -e "\n${RED}Machine stats :$NC " ; uptime
    echo -e "\n${RED}Current network location :$NC " ; scselect
    echo -e "\n${RED}Public facing IP Address :$NC " ;curl myip.ipip.net
    #echo -e "\n${RED}DNS Configuration:$NC " ; scutil --dns
    echo
}

# Desc: Grabs headers from web page
function httpHeaders () { curl -I -L $@ ; }

# Desc: Download a web page and show info on what took time
function httpDebug () { curl $@ -o /dev/null -w "dns: %{time_namelookup} connect: %{time_connect} pretransfer: %{time_pretransfer} starttransfer: %{time_starttransfer} total: %{time_total}\n" ; }

# Desc: 打印当前tmux所有的pane id
function tping() {
    for p in $(tmux list-windows -F "#{pane_id}"); do
        tmux send-keys -t $p Enter
    done
}

# Desc: tmux 中自动起一个窗口去做操作
function tt() {
    if [ $# -lt 1 ]; then
        echo 'usage: tt <commands...>'
        return 1
    fi

    local head="$1"
    local tail='echo -n Press enter to finish.; read'

    while [ $# -gt 1 ]; do
        shift
        tmux split-window "$SHELL -ci \"$1; $tail\""
        tmux select-layout tiled > /dev/null
    done

    tmux set-window-option synchronize-panes on > /dev/null
    $SHELL -ci "$head; $tail"
}

# Desc: tmux 生成一个执行 参数中的命令的临时窗口 回车后自动关闭
function tx() {
    tmux splitw "$*; echo -n Press enter to finish.; read"
    tmux select-layout tiled
    tmux last-pane
}


# Shortcut functions
# --------------------------------------------------------------------

# Desc: vim 编辑which命令找到的文件地址
function viw() {
    vim `which "$1"`
}

# Desc: cat 打印which命令找到的文件地址
function catw() {
    cat `which "$1"`
}

# Desc: ll 打印which命令找到的文件地址
function llw() {
    ls -l `which "$1"`
}

# Desc: 删除 which命令找到的文件
function rmw() {
    rm -f `which "$1"`
}

# Desc: cd 包含参数的名称的文件夹
function gdto() {
    [ "$1" ] && cd *$1*
}

# Desc: cd 命令所在的文件夹
function cdto() {
    cd `dirname $(which "$1")`
}

# Desc: cd 命令所在的文件夹
function cdw() {
    cd `dirname $(which "$1")`
}

# Desc: 生成【参数为后缀名的】的数据文件
function csbuild() {
    [ $# -eq 0 ] && return

    cmd="find `pwd`"
    for ext in $@; do
        cmd=" $cmd -name '*.$ext' -o"
    done
    echo ${cmd: 0: ${#cmd} - 3}
    eval "${cmd: 0: ${#cmd} - 3}" > cscope.files &&
        cscope -b -q && rm cscope.files
}

# Desc: rvm多个版本的gem操作同一个包
function gems() {
    for v in 2.0.0 1.8.7 jruby 1.9.3; do
        rvm use $v
        gem $@
    done
}

# Desc: rvm多个版本的rake操作同一个包
function rakes() {
    for v in 2.0.0 1.8.7 jruby 1.9.3; do
        rvm use $v
        rake $@
    done
}


# Desc: git压缩HEAD版本为zip包
function gitzip() {
    git archive -o $(basename $PWD).zip HEAD
}

# Desc: git压缩HEAD版本为tgz包
function gittgz() {
    git archive -o $(basename $PWD).tgz HEAD
}

# Desc: git 比对两个分支
function gitdiffb() {
    if [ $# -ne 2 ]; then
        echo two branch names required
        return
    fi
    git log --graph \
        --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr)%Creset' \
        --abbrev-commit --date=relative $1..$2
}

# Desc: 最简化 终端主题
function miniprompt() {
    unset PROMPT_COMMAND
    PS1="\[\e[38;5;168m\]> \[\e[0m\]"
}

# boot2docker
# --------------------------------------------------------------------
if [ "$PLATFORM" = 'Darwin' ]; then
    # Desc: docker初始化
    function dockerinit() {
        [ $(docker-machine status default) = 'Running' ] || docker-machine start default
        eval "$(docker-machine env default)"
    }

    # Desc: docker停止
    function dockerstop() {
        docker-machine stop default
    }

    # Desc: 图片压缩
    function resizes() {
        mkdir -p out &&
        for jpg in *.JPG; do
            echo $jpg
            [ -e out/$jpg ] || sips -Z 2048 --setProperty formatOptions 80 $jpg --out out/$jpg
        done
    }

    # Desc: 设置环境变量JAVA_HOME
    function j() { export JAVA_HOME=$(/usr/libexec/java_home -v1.$1); }
fi


# fzf (https://github.com/junegunn/fzf)
# --------------------------------------------------------------------

# Desc: cd to selected directory
function fd() {
    DIR=`find ${1:-*} -path '*/\.*' -prune -o -type d -print 2> /dev/null | fzf-tmux` \
        && cd "$DIR"
}

# Desc: including hidden directories
function fda() {
    DIR=`find ${1:-.} -type d 2> /dev/null | fzf-tmux` && cd "$DIR"
}

# Desc: Figlet font selector
function fgl() {
    cd /usr/local/Cellar/figlet/*/share/figlet/fonts
    BASE=`pwd`
    figlet -f `ls *.flf | sort | fzf` $*
}

# Desc: checkout git branch
function fbr() {
    local branches branch
    branches=$(git branch --all | grep -v HEAD) &&
        branch=$(echo "$branches" |
    fzf-tmux -d $(( 2 + $(wc -l <<< "$branches") )) +m) &&
        git checkout $(echo "$branch" | sed "s/.* //" | sed "s#remotes/[^/]*/##")
}

# Desc: checkout git branch/tag
function fco() {
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

# Desc: checkout git branch/tag, with a preview showing the commits between the tag/branch and HEAD
function fco_preview() {
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

# Desc: checkout git commit
function fcoc() {
  local commits commit
  commits=$(git log --pretty=oneline --abbrev-commit --reverse) &&
  commit=$(echo "$commits" | fzf --tac +s +m -e) &&
  git checkout $(echo "$commit" | sed "s/ .*//")
}

# Desc: get git commit sha. example usage: git rebase -i `fcs`
function fcs() {
  local commits commit
  commits=$(git log --color=always --pretty=oneline --abbrev-commit --reverse) &&
  commit=$(echo "$commits" | fzf --tac +s +m -e --ansi --reverse) &&
  echo -n $(echo "$commit" | sed "s/ .*//")
}

# Desc: pick files from `git status -s`
function is_in_git_repo() {
  git rev-parse HEAD > /dev/null 2>&1
}

# Desc: 显示当前git版本库中未添加进版本的修改或新增文件列表
function fgst() {
  is_in_git_repo || return

  local cmd="${FZF_CTRL_T_COMMAND:-"command git status -s"}"

  eval "$cmd" | FZF_DEFAULT_OPTS="--height ${FZF_TMUX_HEIGHT:-40%} --reverse $FZF_DEFAULT_OPTS $FZF_CTRL_T_OPTS" fzf -m "$@" | while read -r item; do
    echo "$item" | awk '{print $2}'
  done
  echo
}

# Desc: easier way to deal with stashes.
# type fstash to get a list of your stashes.
# enter shows you the contents of the stash.
# ctrl-d shows a diff of the stash against your current HEAD.
# ctrl-b checks the stash out as a branch, for easier merging
function fstash() {
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

# Desc: git commit browser
function fshow() {
git log --graph --color=always \
    --format="%C(auto)%h%d %s %C(black)%C(bold)%cr" "$@" |
fzf --ansi --no-sort --reverse --tiebreak=index --bind=ctrl-s:toggle-sort \
    --bind "ctrl-m:execute:
(grep -o '[a-f0-9]\{7\}' | head -1 |
xargs -I % sh -c 'git show --color=always % | less -R') << 'FZF-EOF'
{}"
}

# Desc: search ctags
function ftags() {
    local line
    [ -e tags ] &&
        line=$(
    awk 'BEGIN { FS="\t" } !/^!/ {print toupper($4)"\t"$1"\t"$2"\t"$3}' tags |
    cut -c1-80 | fzf --nth=1,2
    ) && $EDITOR $(cut -f3 <<< "$line") -c "set nocst" \
        -c "silent tag $(cut -f2 <<< "$line")"
}

#   - Bypass fuzzy finder if there's only one match (--select-1)
#   - Exit if there's no match (--exit-0)
# Desc: Open the selected file with the default editor.
function fe() {
    local file
    file=$(fzf-tmux --query="$1" --select-1 --exit-0)
    [ -n "$file" ] && ${EDITOR:-vim} "$file"
}

#   - CTRL-O to open with `open` command,
#   - CTRL-E or Enter key to open with the $EDITOR
# Desc: Modified version where you can press
function fo() {
    local out file key
    out=$(fzf-tmux --query="$1" --exit-0 --expect=ctrl-o,ctrl-e)
    key=$(head -1 <<< "$out")
    file=$(head -2 <<< "$out" | tail -1)
    if [ -n "$file" ]; then
        [ "$key" = ctrl-o ] && open "$file" || ${EDITOR:-vim} "$file"
    fi
}

if [ -n "$TMUX_PANE" ]; then
    function fzf_tmux_helper() {
        local sz=$1;  shift
        local cmd=$1; shift
        tmux split-window $sz \
            "bash -c \"\$(tmux send-keys -t $TMUX_PANE \"\$(source ~/.fzf.bash; $cmd)\" $*)\""
    }

    # Desc: tmux中 https://github.com/wellle/tmux-complete.vim
    function fzf_tmux_words() {
        fzf_tmux_helper \
            '-p 40' \
            'tmuxwords.rb --all --scroll 500 --min 5 | fzf --multi | paste -sd" " -'
    }

    # Desc: tmux switch pane (@george-b)
    function ftpane() {
        local panes current_window current_pane target target_window target_pane
        panes=$(tmux list-panes -s -F '#I:#P - #{pane_current_path} #{pane_current_command}')
        current_pane=$(tmux display-message -p '#I:#P')
        current_window=$(tmux display-message -p '#I')

        target=$(echo "$panes" | grep -v "$current_pane" | fzf +m --reverse) || return

        target_window=$(echo $target | awk 'BEGIN{FS=":|-"} {print$1}')
        target_pane=$(echo $target | awk 'BEGIN{FS=":|-"} {print$2}' | cut -c 1)

        if [[ $current_window -eq $target_window ]]; then
            tmux select-pane -t ${target_window}.${target_pane}
        else
            tmux select-pane -t ${target_window}.${target_pane} &&
                tmux select-window -t $target_window
        fi
    }

    # Bind CTRL-X-CTRL-T to tmuxwords.sh
    #bind '"\C-x\C-t": "$(fzf_tmux_words)\e\C-e"'
fi

# Desc: Switch tmux-sessions
function fs() {
    local session
    session=$(tmux list-sessions -F "#{session_name}" | \
        fzf-tmux --query="$1" --select-1 --exit-0) &&
        tmux switch-client -t "$session"
}

# Desc: RVM integration
function frb() {
    local rb
    rb=$(
    (echo system; rvm list | grep ruby | cut -c 4-) |
    awk '{print $1}' |
    fzf-tmux -l 30 +m --reverse) && rvm use $rb
}

# Desc: 
function z() {
    if [[ -z "$*" ]]; then
        cd "$(_z -l 2>&1 | fzf-tmux +s --tac | sed 's/^[0-9,.]* *//')"
    else
        _z "$@" || z
    fi
}

# Desc: v - open files in ~/.viminfo
function v() {
    local files
    files=$(grep '^>' ~/.viminfo | cut -c3- |
    while read line; do
        [ -f "${line/\~/$HOME}" ] && echo "$line"
    done | fzf-tmux -d -m -q "$*" -1) && vim ${files//\~/$HOME}
}

# Desc: c - browse chrome history
function c() {
    local cols sep
    export cols=$(( COLUMNS / 3 ))
    export sep='{::}'

    cp -f ~/Library/Application\ Support/Google/Chrome/Default/History /tmp/h
    sqlite3 -separator $sep /tmp/h \
        "select title, url from urls order by last_visit_time desc" |
    ruby -ne '
    cols = ENV["cols"].to_i
    title, url = $_.split(ENV["sep"])
    len = 0
    puts "\x1b[36m" + title.each_char.take_while { |e|
    if len < cols
        len += e =~ /\p{Han}|\p{Katakana}|\p{Hiragana}|\p{Hangul}/ ? 2 : 1
    end
    }.join + " " * (2 + cols - len) + "\x1b[m" + url' |
    fzf --ansi --multi --no-hscroll --tiebreak=index |
    sed 's#.*\(https*://\)#\1#' | xargs open
}

# Desc: vf - fuzzy open with vim from anywhere
# ex: vf word1 word2 ... (even part of a file name)
# zsh autoload function
function vf() {
  local files

  files=(${(f)"$(locate -Ai -0 $@ | grep -z -vE '~$' | fzf --read0 -0 -1 -m)"})

  if [[ -n $files ]]
  then
     vim -- $files
     print -l $files[1]
  fi
}

# Desc: fuzzy grep open via ag with line number
function vg() {
  local file
  local line

  read -r file line <<<"$(ag --nobreak --noheading $@ | fzf -0 -1 | awk -F: '{print $1, $2}')"

  if [[ -n $file ]]
  then
     vim $file +$line
  fi
}

# Desc: fdr - cd to selected parent directory
function fdr() {
  local declare dirs=()
  function get_parent_dirs() {
    if [[ -d "${1}" ]]; then dirs+=("$1"); else return; fi
    if [[ "${1}" == '/' ]]; then
      for _dir in "${dirs[@]}"; do echo $_dir; done
    else
      get_parent_dirs $(dirname "$1")
    fi
  }
  local DIR=$(get_parent_dirs $(realpath "${1:-$PWD}") | fzf-tmux --tac)
  cd "$DIR"
}

# Desc: cf - fuzzy cd from anywhere
# ex: cf word1 word2 ... (even part of a file name)
# zsh autoload function
function cf() {
  local file

  file="$(locate -Ai -0 $@ | grep -z -vE '~$' | fzf --read0 -0 -1)"

  if [[ -n $file ]]
  then
     if [[ -d $file ]]
     then
        cd -- $file
     else
        cd -- ${file:h}
     fi
  fi
}

# Desc: cdff - cd into the directory of the selected file
function cdff() {
   local file
   local dir
   file=$(fzf +m -q "$1") && dir=$(dirname "$file") && cd "$dir"
}

# Desc: fh - repeat history
function fh() {
  eval $( ([ -n "$ZSH_NAME" ] && fc -l 1 || history) | fzf +s --tac | sed 's/ *[0-9]* *//')
}

# Desc: fkill - kill processes - list only the ones you can kill. Modified the earlier script.
function fkill() {
    local pid 
    if [ "$UID" != "0" ]; then
        pid=$(ps -f -u $UID | sed 1d | fzf -m | awk '{print $2}')
    else
        pid=$(ps -ef | sed 1d | fzf -m | awk '{print $2}')
    fi  

    if [ "x$pid" != "x" ]
    then
        echo $pid | xargs kill -${1:-9}
    fi  
}

# Desc: Install one or more versions of specified language
# e.g. `vmi rust` # => fzf multimode, tab to mark, enter to install
# if no plugin is supplied (e.g. `vmi<CR>`), fzf will list them for you
# Mnemonic [V]ersion [M]anager [I]nstall
function vmi() {
  local lang=${1}

  if [[ ! $lang ]]; then
    lang=$(asdf plugin-list | fzf)
  fi

  if [[ $lang ]]; then
    local versions=$(asdf list-all $lang | fzf -m)
    if [[ $versions ]]; then
      for version in $(echo $versions); do
        asdf install $lang $version;
      done;
    fi
  fi
}

# Desc: Remove one or more versions of specified language
# e.g. `vmi rust` # => fzf multimode, tab to mark, enter to remove
# if no plugin is supplied (e.g. `vmi<CR>`), fzf will list them for you
# Mnemonic [V]ersion [M]anager [C]lean
function vmc() {
  local lang=${1}

  if [[ ! $lang ]]; then
    lang=$(asdf plugin-list | fzf)
  fi

  if [[ $lang ]]; then
    local versions=$(asdf list $lang | fzf -m)
    if [[ $versions ]]; then
      for version in $(echo $versions); do
        asdf uninstall $lang $version; 
      done;
    fi
  fi
}

#Homebrew
# Desc: Brew Install (one or multiple) selected application(s)
# using "brew search" as source input
# mnemonic [B]rew [I]nstall [P]lugin
function bip() {
  local inst=$(brew search | fzf -m)

  if [[ $inst ]]; then
    for prog in $(echo $inst);do
        brew install $prog;
    done;
  fi
}

# Desc: Brew Update (one or multiple) selected application(s)
# mnemonic [B]rew [U]pdate [P]lugin
function bup() {
  local upd=$(brew leaves | fzf -m)

  if [[ $upd ]]; then
    for prog in $(echo $upd);do
        brew upgrade $prog;
    done;
  fi
}

# Desc: Brew Delete (one or multiple) selected application(s)
# mnemonic (e.g. uninstall)
function bdl() {
  local uninst=$(brew leaves | fzf -m)

  if [[ $uninst ]]; then
    for prog in $(echo $uninst); do
        brew uninstall $prog; 
    done;
  fi
}

# Desc: 
function fcd() {
    if [[ "$#" != 0 ]]; then
        builtin cd "$@";
        return
    fi
    while true; do
        local lsd=$(echo ".." && ls -p | grep '/$' | sed 's;/$;;')
        local dir="$(printf '%s\n' "${lsd[@]}" |
            fzf --reverse --preview '
                __cd_nxt="$(echo {})";
                __cd_path="$(echo $(pwd)/${__cd_nxt} | sed "s;//;/;")";
                echo $__cd_path;
                echo;
                gls -p --color=always "${__cd_path}";
        ')"
        [[ ${#dir} != 0 ]] || return 0
        builtin cd "$dir" &> /dev/null
    done
}

#-----------------------------------------

# Desc: acd 操作？
function acdul() {
    acdcli ul -x 8 -r 4 -o "$@"
}

# Desc: 删除.DS_Store文件
function removeDS() {
    if [ "" = "$1" ]; then
        find . -type f -name '*.DS_Store' -ls -delete
    else
        find $1 -type f -name '*.DS_Store' -ls -delete
    fi
}

# Desc: 删除到回收站
function mtrash () {
    local path
    for path in "$@"; do
        # ignore any arguments
        if [[ "$path" = -* ]]; then :
        else
            local dst=${path##*/}
            # append the time if necessary
            while [ -e ~/.Trash/"$dst" ]; do
                dst="$dst "$(date +%H-%M-%S)
            done
            mv "$path" ~/.Trash/"$dst"
        fi
    done
}

# Desc: 删除后缀名为参数值的文件到回收站
function rmext () {
    if [ "" = "$1" ]; then
        trash ./*
    else
        trash ./*$1
    fi
}

# Desc: zsh获取WiFi网速
function zsh_wifi_signal(){
    if [ "$MYSYSNAME" = "Mac" ]; then
        local output=$(/System/Library/PrivateFrameworks/Apple80211.framework/Versions/A/Resources/airport -I)
        local airport=$(echo $output | grep 'AirPort' | awk -F': ' '{print $2}')

        if [ "$airport" = "Off" ]; then
                local color='%F{yellow}'
                echo -n "%{$color%}Wifi Off"
        else
                local ssid=$(echo $output | grep ' SSID' | awk -F': ' '{print $2}')
                local speed=$(echo $output | grep 'lastTxRate' | awk -F': ' '{print $2}')
                local color='%F{yellow}'

                [[ $speed -gt 100 ]] && color='%F{green}'
                [[ $speed -lt 50 ]] && color='%F{red}'

                echo -n "%{$color%}WIFI:$ssid SPEED:$speed Mb/s%{%f%}" # removed char not in my PowerLine font
        fi
    elif [ "$MYSYSNAME" = "Centos" ] || [ "$MYSYSNAME" = "Ubuntu" ]; then
        local signal=$(nmcli device wifi | grep yes | awk '{print $8}')
        local color='%F{yellow}'
        [[ $signal -gt 75 ]] && color='%F{green}'
        [[ $signal -lt 50 ]] && color='%F{red}'
        echo -n "%{$color%}\uf230  $signal%{%f%}" # \uf230 is 
    fi
}

# Desc: zsh电池图
function zsh_battery_charge {
  echo `~/bin/battery.py`
}

# Desc: short for cdfinder
function mcdf () {
  cd "`osascript -e 'tell app "Finder" to POSIX path of (insertion location as alias)'`"
}

# Desc: 变更权限rwx为权限值【777】
function mla() {
   ls -l  "$@" | awk '
    {
      k=0;
      for (i=0;i<=8;i++)
        k+=((substr($1,i+2,1)~/[rwx]/) *2^(8-i));
      if (k)
        printf("%0o ",k);
      printf(" %9s  %3s %2s %5s  %6s  %s %s %s\n", $3, $6, $7, $8, $5, $9,$10, $11);
    }'
}

# Desc: 变更权限rwx为权限值
function mqfind () {
  find . -exec grep -l -s $1 {} \;
  return 0
}

# Desc: whois网址信息查询
function mwhois() {
  local domain=$(echo "$1" | awk -F/ '{print $3}') # get domain from URL
  if [ -z $domain ] ; then
    domain=$1
  fi
  echo "Getting whois record for: $domain …"

  # avoid recursion
          # this is the best whois server
                          # strip extra fluff
  /usr/bin/whois -h whois.internic.net $domain | sed '/NOTICE:/q'
}

function customcd() { builtin cd "$@";}

# Desc: 更新git的目录及git module的目录
function upgitfiles() {
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

# Desc: git更新zsh自定义的文件
function upzshcustoms() {
    upgitfiles $MYRUNTIME/oh-my-zsh/custom/plugins
    upgitfiles $MYRUNTIME/oh-my-zsh/antigen
    upgitfiles $MYRUNTIME/oh-my-zsh/custom/themes/powerlevel9k
}

# Desc: git 更新$MYRUNTIME 目录下的所有由git管理的目录
function updotfiles() {
    upgitfiles
}

# Desc: git 更新 插件目录
function upplugins() {
    upgitfiles $MYRUNTIME/public
    customcd ~
}

# Desc: git 更新$MYRUNTIME 目录下的所有由git管理的目录
function upruntimes() {
    updotfiles
    upplugins
}

# Desc: 重新安装neovim
function reinstallneovim() {
    brew reinstall neovim --HEAD
}

# Desc: 每天一更新
function upday() {
    upruntimes
    upzshcustoms
    upzshcustoms
    brew update  && brew upgrade && brew cleanup && brew prune
    /usr/local/sbin/gethosts
}

# Desc: 删除~/.ssh/tmp/*
function rmsshtmp() {
    /bin/rm -f $HOME/.ssh/tmp/*
}

# Desc: 文件夹显示隐藏文件
function showF() { defaults write com.apple.Finder AppleShowAllFiles YES ; }

# Desc: 文件夹不显示隐藏文件
function hideF() { defaults write com.apple.Finder AppleShowAllFiles NO ; }

# Desc: 显示我的自定义SHELL头信息
function myMessage() {
clear
  _COLUMNS=$(tput cols)
  source $MYRUNTIME/tools/m_title
  y=$(( ( $_COLUMNS - ${#_TITLE} )  / 2 ))
  spaces=$(printf "%-${y}s" " ")
  echo " "
  echo -e "${spaces}\033[41;37;5m ${_TITLE} \033[0m"
  echo " "


  _COLUMNS=$(tput cols)
  source $MYRUNTIME/tools/m_message
  y=$(( ( $_COLUMNS - ${#_MESSAGE} )  / 2 ))
  spaces=$(printf "%-${y}s" " ")
  echo -e "${spaces}${_MESSAGE}"
  echo " "
  for ((i=1; i<=$(tput cols); i ++))  ; do echo -n '*';done

  echo " "
}

# Desc: 显示从a-z的我的自定义命令
function ccc() {
    echo "********************************************************"
    echo "*** Already exists command:"
    echo "********************************************************"
    for word in {a..z}; do
        if [ "$(command -v $word)" != "" ]; then
            type $word | grep -v 'not found';
            if [ "$nowshell" != "bash" ]; then
                echo "________________________________________________________"
                which $word | grep -v 'not found';
            fi
            echo "________________________________________________________"
            echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
        fi
    done
}
