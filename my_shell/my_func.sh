cd() { builtin cd "$@"; /bin/ls -aGH; }               # Always list directory contents upon 'cd'
mcd () { mkdir -p "$1" && cd "$1"; }        # mcd:          Makes new Dir and jumps inside
trash () { command mv "$@" ~/.Trash ; }     # trash:        Moves a file to the MacOS trash
ql () { qlmanage -p "$*" >& /dev/null; }    # ql:           Opens any file in MacOS Quicklook Preview
#   mans:   Search manpage given in agument '1' for term given in argument '2' (case insensitive)
#           displays paginated result with colored search terms and two lines surrounding each hit.             Example: mans mplayer codec
#   --------------------------------------------------------------------
mans () {
    man $1 | grep -iC2 --color=always $2 | less
}

#   showa: to remind yourself of an alias (given some part of it)
#   ------------------------------------------------------------
showa () { /usr/bin/grep --color=always -i -a1 $@ ~/Library/init/bash/aliases.bash | grep -v '^\s*$' | less -FSRXc ; }

#   -------------------------------
#   3.  FILE AND FOLDER MANAGEMENT
#   -------------------------------
zipf () { zip -r "$1".zip "$1" ; }          # zipf:         To create a ZIP archive of a folder

#   extract:  Extract most know archives with one command
#   ---------------------------------------------------------
extract () {
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
ff () { /usr/bin/find . -name "$@" ; }      # ff:       Find file under the current directory
ffs () { /usr/bin/find . -name "$@"'*' ; }  # ffs:      Find file whose name starts with a given string
ffe () { /usr/bin/find . -name '*'"$@" ; }  # ffe:      Find file whose name ends with a given string

#   spotlight: Search for a file using MacOS Spotlight's metadata
#   -----------------------------------------------------------
spotlight () { mdfind "kMDItemDisplayName == '$@'wc"; }


#   ---------------------------
#   5.  PROCESS MANAGEMENT
#   ---------------------------
#   findPid: find out the pid of a specified process
#   -----------------------------------------------------
#       Note that the command name can be specified via a regex
#       E.g. findPid '/d$/' finds pids of all processes with names ending in 'd'
#       Without the 'sudo' it will only find processes of the current user
#   -----------------------------------------------------
findPid () { lsof -t -c "$@" ; }

#####my_ps: List processes owned by my user:
my_ps() { ps $@ -u $USER -o pid,%cpu,%mem,start,time,bsdtime,command ; }

#####ii:  display useful host related informaton
ii() {
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

httpHeaders () { curl -I -L $@ ; }             # httpHeaders:      Grabs headers from web page

#####httpDebug:  Download a web page and show info on what took time
httpDebug () { curl $@ -o /dev/null -w "dns: %{time_namelookup} connect: %{time_connect} pretransfer: %{time_pretransfer} starttransfer: %{time_starttransfer} total: %{time_total}\n" ; }

tping() {
    for p in $(tmux list-windows -F "#{pane_id}"); do
        tmux send-keys -t $p Enter
    done
}

tt() {
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


# Shortcut functions
# --------------------------------------------------------------------

viw() {
    vim `which "$1"`
}

gdto() {
    [ "$1" ] && cd *$1*
}

csbuild() {
    [ $# -eq 0 ] && return

    cmd="find `pwd`"
    for ext in $@; do
        cmd=" $cmd -name '*.$ext' -o"
    done
    echo ${cmd: 0: ${#cmd} - 3}
    eval "${cmd: 0: ${#cmd} - 3}" > cscope.files &&
        cscope -b -q && rm cscope.files
}

gems() {
    for v in 2.0.0 1.8.7 jruby 1.9.3; do
        rvm use $v
        gem $@
    done
}

rakes() {
    for v in 2.0.0 1.8.7 jruby 1.9.3; do
        rvm use $v
        rake $@
    done
}

tx() {
    tmux splitw "$*; echo -n Press enter to finish.; read"
    tmux select-layout tiled
    tmux last-pane
}

gitzip() {
    git archive -o $(basename $PWD).zip HEAD
}

gittgz() {
    git archive -o $(basename $PWD).tgz HEAD
}

gitdiffb() {
    if [ $# -ne 2 ]; then
        echo two branch names required
        return
    fi
    git log --graph \
        --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr)%Creset' \
        --abbrev-commit --date=relative $1..$2
}

miniprompt() {
    unset PROMPT_COMMAND
    PS1="\[\e[38;5;168m\]> \[\e[0m\]"
}

# boot2docker
# --------------------------------------------------------------------
if [ "$PLATFORM" = 'Darwin' ]; then
    dockerinit() {
        [ $(docker-machine status default) = 'Running' ] || docker-machine start default
        eval "$(docker-machine env default)"
    }

    dockerstop() {
        docker-machine stop default
    }

    resizes() {
        mkdir -p out &&
        for jpg in *.JPG; do
            echo $jpg
            [ -e out/$jpg ] || sips -Z 2048 --setProperty formatOptions 80 $jpg --out out/$jpg
        done
    }

    j() { export JAVA_HOME=$(/usr/libexec/java_home -v1.$1); }

    # https://gist.github.com/Andrewpk/7558715
    alias startvpn="sudo launchctl load -w /Library/LaunchDaemons/net.juniper.AccessService.plist; open -a '/Applications/Junos Pulse.app/Contents/Plugins/JamUI/PulseTray.app/Contents/MacOS/PulseTray'"
    alias quitvpn="osascript -e 'tell application \"PulseTray.app\" to quit';sudo launchctl unload -w /Library/LaunchDaemons/net.juniper.AccessService.plist"
fi


# fzf (https://github.com/junegunn/fzf)
# --------------------------------------------------------------------

# fd - cd to selected directory
fd() {
    DIR=`find ${1:-*} -path '*/\.*' -prune -o -type d -print 2> /dev/null | fzf-tmux` \
        && cd "$DIR"
}

# fda - including hidden directories
fda() {
    DIR=`find ${1:-.} -type d 2> /dev/null | fzf-tmux` && cd "$DIR"
}

# Figlet font selector
fgl() {
    cd /usr/local/Cellar/figlet/*/share/figlet/fonts
    BASE=`pwd`
    figlet -f `ls *.flf | sort | fzf` $*
}

# fbr - checkout git branch
fbr() {
    local branches branch
    branches=$(git branch --all | grep -v HEAD) &&
        branch=$(echo "$branches" |
    fzf-tmux -d $(( 2 + $(wc -l <<< "$branches") )) +m) &&
        git checkout $(echo "$branch" | sed "s/.* //" | sed "s#remotes/[^/]*/##")
}

# fco - checkout git branch/tag
fco() {
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

# fshow - git commit browser
fshow() {
git log --graph --color=always \
    --format="%C(auto)%h%d %s %C(black)%C(bold)%cr" "$@" |
fzf --ansi --no-sort --reverse --tiebreak=index --bind=ctrl-s:toggle-sort \
    --bind "ctrl-m:execute:
(grep -o '[a-f0-9]\{7\}' | head -1 |
xargs -I % sh -c 'git show --color=always % | less -R') << 'FZF-EOF'
{}"
}

# ftags - search ctags
ftags() {
    local line
    [ -e tags ] &&
        line=$(
    awk 'BEGIN { FS="\t" } !/^!/ {print toupper($4)"\t"$1"\t"$2"\t"$3}' tags |
    cut -c1-80 | fzf --nth=1,2
    ) && $EDITOR $(cut -f3 <<< "$line") -c "set nocst" \
        -c "silent tag $(cut -f2 <<< "$line")"
}

# fe [FUZZY PATTERN] - Open the selected file with the default editor
#   - Bypass fuzzy finder if there's only one match (--select-1)
#   - Exit if there's no match (--exit-0)
fe() {
    local file
    file=$(fzf-tmux --query="$1" --select-1 --exit-0)
    [ -n "$file" ] && ${EDITOR:-vim} "$file"
}

# Modified version where you can press
#   - CTRL-O to open with `open` command,
#   - CTRL-E or Enter key to open with the $EDITOR
fo() {
    local out file key
    out=$(fzf-tmux --query="$1" --exit-0 --expect=ctrl-o,ctrl-e)
    key=$(head -1 <<< "$out")
    file=$(head -2 <<< "$out" | tail -1)
    if [ -n "$file" ]; then
        [ "$key" = ctrl-o ] && open "$file" || ${EDITOR:-vim} "$file"
    fi
}

if [ -n "$TMUX_PANE" ]; then
    fzf_tmux_helper() {
        local sz=$1;  shift
        local cmd=$1; shift
        tmux split-window $sz \
            "bash -c \"\$(tmux send-keys -t $TMUX_PANE \"\$(source ~/.fzf.bash; $cmd)\" $*)\""
    }

    # https://github.com/wellle/tmux-complete.vim
    fzf_tmux_words() {
        fzf_tmux_helper \
            '-p 40' \
            'tmuxwords.rb --all --scroll 500 --min 5 | fzf --multi | paste -sd" " -'
    }

    # ftpane - switch pane (@george-b)
    ftpane() {
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

elif [ -d ~/github/iTerm2-Color-Schemes/ ]; then
    ftheme() {
        local base
        base=~/github/iTerm2-Color-Schemes
        $base/tools/preview.rb "$(
        ls {$base/schemes,~/.vim/plugged/seoul256.vim/iterm2}/*.itermcolors | fzf)"
    }
fi

# Switch tmux-sessions
fs() {
    local session
    session=$(tmux list-sessions -F "#{session_name}" | \
        fzf-tmux --query="$1" --select-1 --exit-0) &&
        tmux switch-client -t "$session"
}

# RVM integration
frb() {
    local rb
    rb=$(
    (echo system; rvm list | grep ruby | cut -c 4-) |
    awk '{print $1}' |
    fzf-tmux -l 30 +m --reverse) && rvm use $rb
}

z() {
    if [[ -z "$*" ]]; then
        cd "$(_z -l 2>&1 | fzf-tmux +s --tac | sed 's/^[0-9,.]* *//')"
    else
        _z "$@" || z
    fi
}

# v - open files in ~/.viminfo
v() {
    local files
    files=$(grep '^>' ~/.viminfo | cut -c3- |
    while read line; do
        [ -f "${line/\~/$HOME}" ] && echo "$line"
    done | fzf-tmux -d -m -q "$*" -1) && vim ${files//\~/$HOME}
}

# c - browse chrome history
c() {
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

acdul() {
    acdcli ul -x 8 -r 4 -o "$@"
}

removeDS() {
    if [ "" = "$1" ]; then
        find . -type f -name '*.DS_Store' -ls -delete
    else
        find $1 -type f -name '*.DS_Store' -ls -delete
    fi
}

mtrash () {
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

rmext () {
    if [ "" = "$1" ]; then
        trash ./*
    else
        trash ./*$1
    fi
}

#zsh获取WiFi网速
zsh_wifi_signal(){
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

function zsh_battery_charge {
  echo `~/bin/battery.py`
}

mcdf () {  # short for cdfinder
  cd "`osascript -e 'tell app "Finder" to POSIX path of (insertion location as alias)'`"
}

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

mqfind () {
  find . -exec grep -l -s $1 {} \;
  return 0
}

mwhois() {
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

customcd() { builtin cd "$@";}

upgitfiles() {
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

upzshcustoms() {
    upgitfiles $MYRUNTIME/oh-my-zsh/custom/plugins
    upgitfiles $MYRUNTIME/oh-my-zsh/antigen
    upgitfiles $MYRUNTIME/oh-my-zsh/custom/themes/powerlevel9k
}

updotfiles() {
    upgitfiles
}

upplugins() {
    upgitfiles $MYRUNTIME/public
    customcd ~
}

upruntimes() {
    updotfiles
    upplugins
}

reinstallneovim() {
    brew reinstall neovim --HEAD
}

upday() {
    upruntimes
    upzshcustoms
    upzshcustoms
    brew update  && brew upgrade && brew cleanup && brew prune
    /usr/local/sbin/gethosts
}

rmsshtmp() {
    /bin/rm -f $HOME/.ssh/tmp/*
}

tm() {
    /usr/local/bin/tmux
}

function showF() { defaults write com.apple.Finder AppleShowAllFiles YES ; }
function hideF() { defaults write com.apple.Finder AppleShowAllFiles NO ; }

myMessage() {
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

ccc() {
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
