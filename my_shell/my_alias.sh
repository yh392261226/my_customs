#####重定向 别名
#Editor
#----------------------------------------------------------------------------------------------------------------
[[ -f /opt/homebrew/opt/macvim/bin/mvim ]] && alias vim="/opt/homebrew/opt/macvim/bin/mvim -v"                   # Desc: alias: vim:(M1)设置环境变量为/opt/homebrew/opt/macvim/bin/mvim -v
[[ -f /usr/local/opt/macvim/bin/mvim ]] && alias vim="/usr/local/opt/macvim/bin/mvim -v"                         # Desc: alias: vim:(Intel)设置环境变量为/usr/local/opt/macvim/bin/mvim -v
[[ -f /usr/bin/vim ]] && alias lvi='/usr/bin/vim'                                                                # Desc: alias: lvi:使用系统的vim版本
[[ -f /opt/homebrew/bin/vim ]] && alias vi='/opt/homebrew/bin/vim'                                               # Desc: alias: vi:(M1)设置环境变量为/opt/homebrew/bin/vim
[[ -f /usr/local/bin/vim ]] && alias vi='/usr/local/bin/vim'                                                     # Desc: alias: vi:(Intel)设置环境变量为/usr/local/bin/vim
[[ -f /opt/homebrew/bin/nvim ]] && alias nvi="/opt/homebrew/bin/nvim"                                            # Desc: alias: nvi:(M1)设置环境变量为/opt/homebrew/bin/nvim
[[ -f /usr/local/bin/nvim ]] && alias nvi="/usr/local/bin/nvim"                                                  # Desc: alias: vi:(Intel)设置环境变量为/usr/local/bin/nvim
alias vi2='vi -O2 '                                                                                              # Desc: alias: vi2:同时打开两个vim窗口
alias ephp='vim'                                                                                                 # Desc: alias: ephp:用vim打开
alias epy='vim'                                                                                                  # Desc: alias: epy:用vim打开
alias erb='vim'                                                                                                  # Desc: alias: erb:用vim打开
alias ehtml='vim'                                                                                                # Desc: alias: ehtml:用vim打开
alias vom='vim'                                                                                                  # Desc: alias: vom:用vim打开
alias vum='vim'                                                                                                  # Desc: alias: vum:用vim打开
[[ -f /opt/homebrew/opt/macvim/bin/mvim ]] && alias mvim='/opt/homebrew/opt/macvim/bin/mvim -v'                  # Desc: alias: mvim:(M1)设置环境变量为/opt/homebrew/opt/macvim/bin/mvim -v
[[ -f /usr/local/opt/macvim/bin/mvim ]] && alias mvim='/usr/local/opt/macvim/bin/mvim -v'                        # Desc: alias: mvim:(Intel)设置环境变量为/usr/local/opt/macvim/bin/mvim -v
[[ -f /opt/homebrew/opt/macvim/bin/mvim ]] && alias mvi='/opt/homebrew/opt/macvim/bin/mvim -v'                   # Desc: alias: mvi:(M1)设置环境变量为/opt/homebrew/opt/macvim/bin/mvim -v
[[ -f /usr/local/opt/macvim/bin/mvim ]] && alias mvi='/usr/local/opt/macvim/bin/mvim -v'                         # Desc: alias: mvi:(Intel)设置环境变量为/usr/local/opt/macvim/bin/mvim -v
[[ -f /opt/homebrew/opt/macvim/bin/vimdiff ]] && alias vimdiff="/opt/homebrew/opt/macvim/bin/vimdiff"            # Desc: alias: vimdiff:(M1)设置环境变量为/opt/homebrew/opt/macvim/bin/vimdiff
[[ -f /usr/local/opt/macvim/bin/vimdiff ]] && alias vimdiff="/usr/local/opt/macvim/bin/vimdiff"                  # Desc: alias: vimdiff:(Intel)设置环境变量为/usr/local/opt/macvim/bin/vimdiff
alias ehosts='sudo vim /etc/hosts'                                                                               # Desc: alias: ehosts:以管理员身份用vim打开/etc/hosts
[[ -f /usr/local/bin/code ]] && alias code.="/usr/local/bin/code ."                                              # Desc: alias: code.:设置用vscode打开当前目录

#Directoy && File
#----------------------------------------------------------------------------------------------------------------
alias l='gls -aH --color=tty'                                                                                    # Desc: alias: l:设置为gls列出所有文件(含隐藏)
alias le="exa"                                                                                                   # Desc: alias: le:设置为exa列出所有文件
alias lel="exa -l -a -h -m -n -U --git"                                                                          # Desc: alias: lel:设置为exa列出所有文件详情及git情况
[[ -f /usr/local/bin/lsd ]] && alias cls='/usr/local/bin/lsd'                                                    # Desc: alias: cls:(Intel)设置环境变量为/usr/local/bin/lsd
[[ -f /opt/homebrew/bin/lsd ]] && alias cls='/opt/homebrew/bin/lsd'                                              # Desc: alias: cls:(M1)设置环境变量为/opt/homebrew/bin/lsd
[[ -f /usr/local/bin/ls++ ]] && alias lll="/usr/local/bin/ls++"                                                  # Desc: alias: lll:设置环境变量为/usr/local/bin/ls++
alias ks="lsd -l"                                                                                                # Desc: alias: ks:设置lsd -l命令的别名
alias lv="lsd -la"                                                                                               # Desc: alias: lv:设置lsd -la命令的别名
alias llm='exa -lbGd --git --sort=modified'                                                                      # Desc: alias: llm:long list, modified date sort
alias lea='exa -lbhaF --icons --git --color-scale'                                                               # Desc: alias: lea:all list
alias lla='exa -lbhHigUmuSa --time-style=long-iso --git --color-scale'                                           # Desc: alias: lla:all list
alias lx='exa -lbhHigUmuSa@ --time-style=long-iso --git --color-scale'                                           # Desc: alias: lx:all + extended list
alias lS='exa -1'                                                                                                # Desc: alias: lS:one column, just names
alias lt='exa --tree --level=2'                                                                                  # Desc: alias: lt:tree
alias cd..='cd ../'                                                                                              # Desc: alias: cd..:Go back 1 directory level (for fast typers)
alias cd.='cd ..'                                                                                                # Desc: alias: cd.:Go back 1 directory level (for fast typers)
alias ..='cd ../'                                                                                                # Desc: alias: ..:Go back 1 directory level
alias ...='cd ../../'                                                                                            # Desc: alias: ...:Go back 2 directory levels
alias ....='cd ../../..'                                                                                         # Desc: alias: ....:Go back 3 directory levels
alias .....='cd ../../../..'                                                                                     # Desc: alias: .....:Go back 4 directory levels
alias ......='cd ../../../../..'                                                                                 # Desc: alias: ......:Go back 5 directory levels
alias .3='cd ../../../'                                                                                          # Desc: alias: .3:Go back 3 directory levels
alias .4='cd ../../../../'                                                                                       # Desc: alias: .4:Go back 4 directory levels
alias .5='cd ../../../../../'                                                                                    # Desc: alias: .5:Go back 5 directory levels
alias .6='cd ../../../../../../'                                                                                 # Desc: alias: .6:Go back 6 directory levels
alias numFiles='echo $(ls -1 | wc -l)'                                                                           # Desc: alias: numFiles:Count of non-hidden files in current dir
alias make1mb='mkfile 1m ./1MB.dat'                                                                              # Desc: alias: make1mb:Creates a file of 1mb size (all zeros)
alias make5mb='mkfile 5m ./5MB.dat'                                                                              # Desc: alias: make5mb:Creates a file of 5mb size (all zeros)
alias make10mb='mkfile 10m ./10MB.dat'                                                                           # Desc: alias: make10mb:Creates a file of 10mb size (all zeros)
alias mountReadWrite='/sbin/mount -uw /'                                                                         # Desc: alias: mountReadWrite:For use when booted into single-user
alias finderShow='defaults write com.apple.finder ShowAllFiles TRUE'                                             # Desc: alias: finderShow:显示隐藏文件
alias finderHide='defaults write com.apple.finder ShowAllFiles FALSE'                                            # Desc: alias: finderHide:隐藏隐藏文件
alias tmuxls="ls $TMPDIR/tmux*/"                                                                                 # Desc: alias: tmuxls:列出缓存目录中所有以tmux开头的文件及文件夹
alias du="ncdu --color dark -rr -x --exclude .git --exclude node_modules"                                        # Desc: alias: du:利用ncdu命令进行文件夹大小统计
[[ -f $MYRUNTIME/customs/others/fuzzy-fs/fuzzy-fs ]] && alias fs="fuzzy-fs"                                      # Desc: alias: fs:fuzzy-fs目录管理器
[[ -d $(brew --prefix zoxide) ]] && alias zd="zoxide"                                                            # Desc: alias: zd:zoxide命令的别名
alias dut="$(whereis du) -sh"                                                                                    # Desc: alias: dut:du -sh命令的别名

alias difff="diff-so-fancy"                                                                                      # Desc: alias: difff:diff so fancy命令的别名
alias qfind="find . -name "                                                                                      # Desc: alias: qfind:Quickly search for file
alias filetree="ls -R | grep ":$" | sed -e 's/:$//' -e 's/[^-][^\/]*\//--/g' -e 's/^/ /' -e 's/-/|/'"            # Desc: alias: filetree:按文件树型结构展示目录
[[ -f /opt/homebrew/bin/ccat ]] && alias cat="/opt/homebrew/bin/ccat"                                            # Desc: alias: cat:(M1)设置/opt/homebrew/bin/ccat代替cat命令
[[ -f /usr/local/bin/ccat ]] && alias cat="/usr/local/bin/ccat"                                                  # Desc: alias: cat:(Intel)设置/usr/local/bin/ccat代替cat命令
alias mime='file -bL --mime-type'                                                                                # Desc: alias: mime:获取文件的类型命令

#Compression
#----------------------------------------------------------------------------------------------------------------
alias gz='tar -zxvf'                                                                                             # Desc: alias: gz:tar -zxvf解压缩命令的别名
alias tgz='tar -zxvf'                                                                                            # Desc: alias: tgz:tar -zxvf解压缩命令的别名
alias bz2='tar -xjvf'                                                                                            # Desc: alias: bz2:tar -xjvf解压缩命令的别名

#Brew
#----------------------------------------------------------------------------------------------------------------
alias brewu='brew update && brew upgrade && brew cleanup && brew cleanup --prune-prefix && brew doctor'          # Desc: alias: brewu:brew更新命令的别名
alias brewup='brew update && brew upgrade && brew cleanup && brew cleanup --prune-prefix && brew doctor'         # Desc: alias: brewup:brew更新命令的别名
alias bu='brew update && brew upgrade && brew cleanup'                                                           # Desc: alias: bu:brew更新命令的别名

#Process
#----------------------------------------------------------------------------------------------------------------
alias memHogsTop='top -l 1 -o rsize | head -20'                                                                  # Desc: alias: memHogsTop:列出进程中占用内存最高的20条
alias memHogsPs='ps wwaxm -o pid,stat,vsize,rss,time,command | head -10'                                         # Desc: alias: memHogsPs:列出进程中占用内存最高的10条的详细内容
alias cpu_hogs='ps wwaxr -o pid,stat,%cpu,time,command | head -10'                                               # Desc: alias: cpu_hogs:列出进程中占用cpu最高的前10条
alias topForever='top -l 9999999 -s 10 -o cpu'                                                                   # Desc: alias: topForever:列出进程按照cpu消耗的降序展示
alias ttop="top -R -F -s 10 -o rsize"                                                                            # Desc: alias: ttop:列出进程中前10条

#Network
#----------------------------------------------------------------------------------------------------------------
alias myip="curl myip.ipip.net"                                                                                  # Desc: alias: myip:Public facing IP Address
alias netCons='lsof -i'                                                                                          # Desc: alias: netCons:Show all open TCP/IP sockets
alias flushDNS='dscacheutil -flushcache'                                                                         # Desc: alias: flushDNS:Flush out the DNS Cache
alias lsock='sudo /usr/sbin/lsof -i -P'                                                                          # Desc: alias: lsock:Display open sockets
alias lsockU='sudo /usr/sbin/lsof -nP | grep UDP'                                                                # Desc: alias: lsockU:Display only open UDP sockets
alias lsockT='sudo /usr/sbin/lsof -nP | grep TCP'                                                                # Desc: alias: lsockT:Display only open TCP sockets
alias ipInfo0='ipconfig getpacket en0'                                                                           # Desc: alias: ipInfo0:Get info on connections for en0
alias ipInfo1='ipconfig getpacket en1'                                                                           # Desc: alias: ipInfo1:Get info on connections for en1
alias openPorts='sudo lsof -i | grep LISTEN'                                                                     # Desc: alias: openPorts:All listening connections
alias showBlocked='sudo ipfw list'                                                                               # Desc: alias: showBlocked:All ipfw rules inc/ blocked IPs
alias pping='prettyping'                                                                                         # Desc: alias: pping:a nice way to show ping command result

#Versions
#----------------------------------------------------------------------------------------------------------------
alias gv='git log --graph --format="%C(auto)%h%d %s %C(black)%C(bold)%cr"'                                       # Desc: alias: gv:列出git版本的log日志
alias gcid="git log | head -1 | awk '{print substr(\$2,1,7)}' | pbcopy"                                          # Desc: alias: gcid:复制当前版本日志重第一条的月份
alias gsh="git stash"                                                                                            # Desc: alias: gsh:git stash命令的别名g
alias gd2="git status -s | fzf --no-sort --reverse --preview 'git diff --color=always {+2} | diff-so-fancy' --bind=ctrl-j:preview-down --bind=ctrl-k:preview-up --preview-window=right:60%:wrap"                                                        # Desc: alias: gd2:利用fzf列出当前版本文件中修改的文件并diff
alias g='git'                                                                                                    # Desc: alias: g:git命令的别名
alias gs='git status'                                                                                            # Desc: alias: gs:git status命令的别名
alias gl='git pull'                                                                                              # Desc: alias: gl:git pull命令的别名
alias gup='git fetch && git rebase'                                                                              # Desc: alias: gup:git fetch && git rebase命令的别名
alias gp='git push'                                                                                              # Desc: alias: gp:git push命令的别名
alias gdv='git diff -w "$@" | vim -R -'                                                                          # Desc: alias: gdv:git对比并用vim打开
alias gc='git commit -m'                                                                                         # Desc: alias: gc:git commit -m命令的别名
alias gca='git commit -v -a'                                                                                     # Desc: alias: gca:git commit -v -a命令的别名
alias gb='git branch'                                                                                            # Desc: alias: gb:git branch命令的别名
alias gba='git branch -a'                                                                                        # Desc: alias: gba:git branch -a命令的别名
alias gcount='git shortlog -sn'                                                                                  # Desc: alias: gcount:git shortlog -sn命令的别名
alias git-help='git help'                                                                                        # Desc: alias: git-help:为配合fzf-tab设置git help的别名
alias git-show='git show'                                                                                        # Desc: alias: git-show:为配合fzf-tab设置git show的别名
alias git-log='git log'                                                                                          # Desc: alias: git-log:为配合fzf-tab设置git log的别名
alias git-checkout='git checkout'                                                                                # Desc: alias: git-checkout:为配合fzf-tab设置git checkout的别名
alias lg='lazygit'                                                                                               # Desc: alias: lg:lazygit命令的别名

alias hgs='hg status'                                                                                            # Desc: alias: hgs:hg status命令的别名
alias hgu='hg update'                                                                                            # Desc: alias: hgu:hg update命令的别名
alias hgpl='hg pull'                                                                                             # Desc: alias: hgpl:hg pull命令的别名
alias hgpu='hg push'                                                                                             # Desc: alias: hgpu:hg push命令的别名
alias hgc='hg clone'                                                                                             # Desc: alias: hgc:hg clone命令的别名

# Docker alias
#----------------------------------------------------------------------------------------------------------------
alias dkps="docker ps"                                                                                           # Desc: alias: dkps:docker ps命令的别名
alias dkst="docker stats"                                                                                        # Desc: alias: dkst:docker stats命令的别名
alias dkpsa="docker ps -a"                                                                                       # Desc: alias: dkpsa:docker ps命令的别名
alias dkimgs="docker images"                                                                                     # Desc: alias: dkimgs:docker images命令的别名
alias dkcpup="docker-compose up -d"                                                                              # Desc: alias: dkcpup:docker-compose up -d命令的别名
alias dkcpdown="docker-compose down"                                                                             # Desc: alias: dkcpdown:docker-compose down命令的别名
alias dkcpstart="docker-compose start"                                                                           # Desc: alias: dkcpstart:docker-compose start命令的别名
alias dkcpstop="docker-compose stop"                                                                             # Desc: alias: dkcpstop:docker-compose stop命令的别名

# Cp alias
#----------------------------------------------------------------------------------------------------------------
alias cp='cp -r'                                                                                                 # Desc: alias: cp:复制整个子目录
alias cpr='rsync -PrlpE'                                                                                         # Desc: alias: cpr:rsync上传
alias cpz='rsync -PrlpEz'                                                                                        # Desc: alias: cpz:rsync下载

# Rm alias
#----------------------------------------------------------------------------------------------------------------
alias cleanupLS="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user && killall Finder"                                                                                                  # Desc: alias: cleanupLS:忘记该别名的作用了
alias cleanupDS="find . -type f -name '*.DS_Store' -ls -delete"                                                  # Desc: alias: cleanupDS:查找并删除当前目录中的.DS_Store文件
#alias rm='/usr/local/bin/trash'                                                                                 # Desc: alias: rm:设置为trash替代命令
alias rmDS="remove_DS_files"                                                                                     # Desc: alias: rmDS:removeDS命令的别名
alias rm='rm -i'                                                                                                 # Desc: alias: rm:增加详情选项
alias rmf='rm -rf'                                                                                               # Desc: alias: rmf:增加递归删除选项

# Mkdir alias
#----------------------------------------------------------------------------------------------------------------
alias mk='mkdir -p'                                                                                              # Desc: alias: mk:递归创建目录
alias mkdir='mkdir -p'                                                                                           # Desc: alias: mkdir:增加递归创建选项

# Man alias
#----------------------------------------------------------------------------------------------------------------
[[ -d /usr/local/share/man/zh_CN ]] && alias cnman='man -M /usr/local/share/man/zh_CN'                           # Desc: alias: cnman:(Intel)设置中文man命令为man -M /usr/local/share/man/zh_CN
[[ -d /opt/homebrew/share/man/zh ]] && alias cnman='man -M /opt/homebrew/share/man/zh'                           # Desc: alias: cnman:(m1)设置中文man命令为man -M /opt/homebrew/share/man/zh
[[ -d /usr/local/share/man/zh_CN ]] && alias cman='man -M /usr/local/share/man/zh_CN'                            # Desc: alias: cman:(Intel)设置中文man命令为man -M /usr/local/share/man/zh_CN
[[ -d /opt/homebrew/share/man/zh ]] && alias cman='man -M /opt/homebrew/share/man/zh'                            # Desc: alias: cman:(m1)设置中文man命令为man -M /opt/homebrew/share/man/zh


#Other
#----------------------------------------------------------------------------------------------------------------
alias woshishei='whoami'                                                                                         # Desc: alias: woshishei:whoami命令的别名
alias screensaverDesktop='/System/Library/Frameworks/ScreenSaver.framework/Resources/ScreenSaverEngine.app/Contents/MacOS/ScreenSaverEngine -background'    # Desc: alias: screensaverDesktop:忘记该别名作用了
alias hc="history -c"                                                                                            # Desc: alias: hc:清空历史命令记录
alias hfd="builtin fc -li | grep $(date -I)"                                                                     # Desc: alias: hfd:列出今天的历史命令记录
alias hfs="builtin fc -li | grep ${2}"                                                                           # Desc: alias: hfs: 按关键字搜索历史命令记录
alias typep='type -p'                                                                                            # Desc: alias: typep: type -p命令的别名
alias cl='clear'                                                                                                 # Desc: alias: cl:清屏
alias woshi='whoami'                                                                                             # Desc: alias: woshi:whoami命令的别名
alias train="$(brew --prefix sl)/bin/sl"                                                                         # Desc: alias: train:命令行小火车跑过命令的别名
[[ -f $MYRUNTIME/customs/bin/game ]] && alias ssq="$MYRUNTIME/customs/bin/game lottery doubleball"               # Desc: alias: ssq: game命令双色球的别名
[[ -f $MYRUNTIME/customs/bin/game ]] && alias mweb="$MYRUNTIME/customs/bin/game web open"                        # Desc: alias: mweb: game命令打开网址的别名
[[ -f $MYRUNTIME/customs/bin/theme ]] && alias thl="$MYRUNTIME/customs/bin/theme --light -i"                     # Desc: alias: thl:theme命令中的亮系主题列表选择器
[[ -f $MYRUNTIME/customs/bin/theme ]] && alias thd="$MYRUNTIME/customs/bin/theme --dark -i"                      # Desc: alias: thd:theme命令中的暗系主题列表选择器
[[ -f /opt/homebrew/bin/code-minimap ]] && alias cmap="code-minimap"                                             # Desc: alias: cmap:code-minimap命令的别名