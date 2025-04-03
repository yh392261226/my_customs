export ZSH=$HOME/.oh-my-zsh
export OMZ=$ZSH
export OMZP=$ZSH/plugins
export OMZP=$HOME/.zinit/plugins
export OMZL=$ZSH/lib
#自动更新时间
export UPDATE_ZSH_DAYS=7
#主题
#ZSH_THEME="j"
#ZSH_THEME="amuse"
#ZSH_THEME="robbyrussell"
#ZSH_THEME="powerline2"
#ZSH_THEME="powerlevel9k/powerlevel9k"
#ZSH_THEME="spaceship"
# ZSH_THEME="cviebrock"
#ZSH_THEME_RANDOM_CANDIDATES=(
#	"amuse"
#	"powerlevel9k/powerlevel9k"
#	"spaceship"
#	"cviebrock"
#	"powerlevel10k/powerlevel10k"
#)
#ZSH_THEME="amuse" 
#ZSH_THEME="powerlevel10k/powerlevel10k"

#plugins setting
#plugins=(git mvn textmate subl autojump svn svn-fast-info brew go history tmux git-flow node osx cp perl python ruby rsync urltools oh-my-zsh-bootstrap zshmarks yoshiori zsh-autosuggestions zsh-syntax-highlighting)
plugins=(
#    ag
	mvn
	autojump
    # bbedit
    colored-man-pages
    colorize
    command-not-found
    copyfile
    copypath
    dnote
    encode64
    git-auto-fetch
#	svn
#	svn-fast-info
	golang
	history
	git-flow
	node
	macos
	cp
	perl
	python
	ruby
	rsync
	urltools
	jsontools
	copypath
	copyfile
	copybuffer
    # fzf-brew
	# zsh-autosuggestions
	# zsh-syntax-highlighting
	# web-search
	# alias-tips
	# zsh-apple-touchbar
	# codeception
	# zsh-iterm-touchbar
	# git-extra-commands
	# history-substring-search
	# zui
	# zbrowse
	# bgnotify
	# zsh-apple-touchbar
	# zsh-interactive-cd
	# fzf-tab
	# fzf-zsh-completions
	# formarks
	# h
	# k
	# mysql-colorize
	) #last-working-dir
autoload -U compinit
[[ -f $HOME/.custom_omz.sh ]] && source $HOME/.custom_omz.sh || touch $HOME/.custom_omz.sh
#&& compinit
ZSH_TMUX_AUTOSTART='true'
ZSH_DISABLE_COMPFIX=true
source $ZSH/oh-my-zsh.sh

HISTFILE=$HOME/data/data/.zsh_history.data
HISTSIZE=500000
SAVEHIST=500000
setopt appendhistory
setopt INC_APPEND_HISTORY  
setopt SHARE_HISTORY

#ZSH的模块加载
zmodload -a zsh/zprof zprof
# zmodload -a zsh/mapfile mapfile
zmodload -a zsh/zpty zpty
zmodload -a zsh/stat zstat
