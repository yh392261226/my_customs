#####重定向 别名
#vim

[[ -f /opt/homebrew/opt/macvim/bin/mvim ]] && alias vim="/opt/homebrew/opt/macvim/bin/mvim -v"                         # vim alias link
[[ -f /usr/local/opt/macvim/bin/mvim ]] && alias vim="/usr/local/opt/macvim/bin/mvim -v"                         # vim alias link
[[ -f /usr/bin/vim ]] && alias vi='/usr/bin/vim'
[[ -f /opt/homebrew/bin/nvim ]] && alias nvi="/opt/homebrew/bin/nvim"
[[ -f /usr/local/bin/nvim ]] && alias nvi="/usr/local/bin/nvim"
alias vi2='vi -O2 '
alias ephp='vim'
alias epy='vim'
alias erb='vim'
alias ehtml='vim'
alias vom='vim'
alias vum='vim'
[[ -f /opt/homebrew/opt/macvim/bin/mvim ]] && alias mvim='/opt/homebrew/opt/macvim/bin/mvim -v'
[[ -f /usr/local/opt/macvim/bin/mvim ]] && alias mvim='/usr/local/opt/macvim/bin/mvim -v'
[[ -f /opt/homebrew/opt/macvim/bin/mvim ]] && alias mvi='/opt/homebrew/opt/macvim/bin/mvim -v'
[[ -f /usr/local/opt/macvim/bin/mvim ]] && alias mvi='/usr/local/opt/macvim/bin/mvim -v'
[[ -f /opt/homebrew/opt/macvim/bin/vimdiff ]] && alias vimdiff="/opt/homebrew/opt/macvim/bin/vimdiff" # vimdiff alias link
[[ -f /usr/local/opt/macvim/bin/vimdiff ]] && alias vimdiff="/usr/local/opt/macvim/bin/vimdiff" # vimdiff alias link
alias ehosts='sudo vim /etc/hosts'          # editHosts:        Edit /etc/hosts fil

#directoy

alias l='gls -aH --color=tty'               # Change the command l to ls -aH
[[ -f /usr/local/bin/lsd ]] && alias cls='/usr/local/bin/lsd'              # byond lsd change ls to colorful ls
[[ -f /opt/homebrew/bin/lsd ]] && alias cls='/opt/homebrew/bin/lsd'              # byond lsd change ls to colorful ls
[[ -f /usr/local/bin/ls++ ]] && alias lll="/usr/local/bin/ls++"
alias ks="ls"
alias cd..='cd ../'                         # Go back 1 directory level (for fast typers)
alias cd.='cd ..'
alias ..='cd ../'                           # Go back 1 directory level
alias ...='cd ../../'                       # Go back 2 directory levels
alias .3='cd ../../../'                     # Go back 3 directory levels
alias .4='cd ../../../../'                  # Go back 4 directory levels
alias .5='cd ../../../../../'               # Go back 5 directory levels
alias .6='cd ../../../../../../'            # Go back 6 directory levels
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias ......='cd ../../../../..'
alias numFiles='echo $(ls -1 | wc -l)'      # numFiles:     Count of non-hidden files in current dir
alias make1mb='mkfile 1m ./1MB.dat'         # make1mb:      Creates a file of 1mb size (all zeros)
alias make5mb='mkfile 5m ./5MB.dat'         # make5mb:      Creates a file of 5mb size (all zeros)
alias make10mb='mkfile 10m ./10MB.dat'      # make10mb:     Creates a file of 10mb size (all zeros)
alias mountReadWrite='/sbin/mount -uw /'    # mountReadWrite:   For use when booted into single-user
alias finderShow='defaults write com.apple.finder ShowAllFiles TRUE'
alias finderHide='defaults write com.apple.finder ShowAllFiles FALSE'
alias tmuxls="ls $TMPDIR/tmux*/"
alias du="ncdu --color dark -rr -x --exclude .git --exclude node_modules"

#files

alias difff="diff-so-fancy" #diff so fancy
alias cleanupDS="find . -type f -name '*.DS_Store' -ls -delete"
alias cleanupLS="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user && killall Finder"
alias qfind="find . -name "                 # qfind:    Quickly search for file
#alias rm='/usr/local/bin/trash'
alias rmDS="removeDS"
alias filetree="ls -R | grep ":$" | sed -e 's/:$//' -e 's/[^-][^\/]*\//--/g' -e 's/^/ /' -e 's/-/|/'"

#compression
alias gz='tar -zxvf'
alias tgz='tar -zxvf'
alias bz2='tar -xjvf'

#brew
alias brewu='brew update && brew upgrade && brew cleanup && brew cleanup --prune-prefix && brew doctor'
alias brewup='brew update && brew upgrade && brew cleanup && brew cleanup --prune-prefix && brew doctor'
alias bu='brew update && brew upgrade && brew cleanup'

#process

alias memHogsTop='top -l 1 -o rsize | head -20'
alias memHogsPs='ps wwaxm -o pid,stat,vsize,rss,time,command | head -10'
alias cpu_hogs='ps wwaxr -o pid,stat,%cpu,time,command | head -10'
alias topForever='top -l 9999999 -s 10 -o cpu'
alias ttop="top -R -F -s 10 -o rsize"

#network

alias myip="curl myip.ipip.net"                    # myip:         Public facing IP Address
alias netCons='lsof -i'                             # netCons:      Show all open TCP/IP sockets
alias flushDNS='dscacheutil -flushcache'            # flushDNS:     Flush out the DNS Cache
alias lsock='sudo /usr/sbin/lsof -i -P'             # lsock:        Display open sockets
alias lsockU='sudo /usr/sbin/lsof -nP | grep UDP'   # lsockU:       Display only open UDP sockets
alias lsockT='sudo /usr/sbin/lsof -nP | grep TCP'   # lsockT:       Display only open TCP sockets
alias ipInfo0='ipconfig getpacket en0'              # ipInfo0:      Get info on connections for en0
alias ipInfo1='ipconfig getpacket en1'              # ipInfo1:      Get info on connections for en1
alias openPorts='sudo lsof -i | grep LISTEN'        # openPorts:    All listening connections
alias showBlocked='sudo ipfw list'                  # showBlocked:  All ipfw rules inc/ blocked IPs
alias pping='prettyping'                            # a nice way to show ping command result

#versions

alias gitv='git log --graph --format="%C(auto)%h%d %s %C(black)%C(bold)%cr"'
alias gcid="git log | head -1 | awk '{print substr(\$2,1,7)}' | pbcopy"
alias gith="git stash"
git config --global alias.co checkout
git config --global alias.ci commit
git config --global alias.cm commit
git config --global alias.st status
git config --global alias.ad add
git config --global alias.df diff
git config --global alias.dfc "diff --cached"
git config --global alias.br branch
git config --global alias.lol "log --graph --decorate --pretty=oneline --abbrev-commit"
git config --global alias.lola "log --graph --decorate --pretty=oneline --abbrev-commit --all"
git config --global alias.subup "submodule update --init --recursive"
git config --global alias.subst "submodule status --recursive"
alias gd2="git status -s \
 | fzf --no-sort --reverse \
 --preview 'git diff --color=always {+2} | diff-so-fancy' \
 --bind=ctrl-j:preview-down --bind=ctrl-k:preview-up \
 --preview-window=right:60%:wrap"
alias hgs='hg status'
alias hgu='hg update'
alias hgpl='hg pull'
alias hgpu='hg push'
alias hgc='hg clone'

# Docker alias
alias dkps="docker ps"
alias dkst="docker stats"
alias dkpsa="docker ps -a"
alias dkimgs="docker images"
alias dkcpup="docker-compose up -d"
alias dkcpdown="docker-compose down"
alias dkcpstart="docker-compose start"
alias dkcpstop="docker-compose stop"

#other
alias screensaverDesktop='/System/Library/Frameworks/ScreenSaver.framework/Resources/ScreenSaverEngine.app/Contents/MacOS/ScreenSaverEngine -background'
alias hc="history -c"
alias typep='type -p'
alias cl='clear'
alias woshi='whoami'
alias dut="$(whereis du) -sh"
alias train="$(brew --prefix sl)/bin/sl"
[[ -d /usr/local/share/man/zh_CN ]] && alias cnman='man -M /usr/local/share/man/zh_CN'
[[ -d /opt/homebrew/share/man/zh ]] && alias cnman='man -M /opt/homebrew/share/man/zh'
[[ -d /usr/local/share/man/zh_CN ]] && alias cman='man -M /usr/local/share/man/zh_CN'
[[ -d /opt/homebrew/share/man/zh ]] && alias cman='man -M /opt/homebrew/share/man/zh'
