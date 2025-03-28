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
#powerlevel9k的主题设置 参考网址：https://github.com/bhilburn/powerlevel9k
### custom setting
##POWERLEVEL9K_MODE='awesome-fontconfig'
##POWERLEVEL9K_PROMPT_ON_NEWLINE=true
##POWERLEVEL9K_SHORTEN_DIR_LENGTH=1
##POWERLEVEL9K_SHORTEN_STRATEGY="truncate_right"
##POWERLEVEL9K_OS_ICON_BACKGROUND="black"
##POWERLEVEL9K_OS_ICON_FOREGROUND="249"
##POWERLEVEL9K_TODO_BACKGROUND="black"
##POWERLEVEL9K_TODO_FOREGROUND="249"
##POWERLEVEL9K_DIR_HOME_BACKGROUND="black"
##POWERLEVEL9K_DIR_HOME_FOREGROUND="249"
##POWERLEVEL9K_DIR_HOME_SUBFOLDER_BACKGROUND="black"
##POWERLEVEL9K_DIR_HOME_SUBFOLDER_FOREGROUND="249"
##POWERLEVEL9K_DIR_DEFAULT_BACKGROUND="black"
##POWERLEVEL9K_DIR_DEFAULT_FOREGROUND="249"
##POWERLEVEL9K_STATUS_OK_BACKGROUND="black"
##POWERLEVEL9K_STATUS_OK_FOREGROUND="yellow"
##POWERLEVEL9K_STATUS_ERROR_BACKGROUND="black"
##POWERLEVEL9K_STATUS_ERROR_FOREGROUND="red"
##POWERLEVEL9K_NVM_BACKGROUND="black"
##POWERLEVEL9K_NVM_FOREGROUND="249"
##POWERLEVEL9K_NVM_VISUAL_IDENTIFIER_COLOR="green"
##POWERLEVEL9K_RVM_BACKGROUND="black"
##POWERLEVEL9K_RVM_FOREGROUND="249"
##POWERLEVEL9K_RVM_VISUAL_IDENTIFIER_COLOR="red"
##POWERLEVEL9K_LOAD_CRITICAL_BACKGROUND="black"
##POWERLEVEL9K_LOAD_WARNING_BACKGROUND="black"
##POWERLEVEL9K_LOAD_NORMAL_BACKGROUND="black"
##POWERLEVEL9K_LOAD_CRITICAL_FOREGROUND="249"
##POWERLEVEL9K_LOAD_WARNING_FOREGROUND="249"
##POWERLEVEL9K_LOAD_NORMAL_FOREGROUND="249"
##POWERLEVEL9K_LOAD_CRITICAL_VISUAL_IDENTIFIER_COLOR="red"
##POWERLEVEL9K_LOAD_WARNING_VISUAL_IDENTIFIER_COLOR="yellow"
##POWERLEVEL9K_LOAD_NORMAL_VISUAL_IDENTIFIER_COLOR="green"
##POWERLEVEL9K_RAM_BACKGROUND="black"
##POWERLEVEL9K_RAM_FOREGROUND="249"
##POWERLEVEL9K_RAM_ELEMENTS=(ram_free)
##POWERLEVEL9K_BATTERY_LOW_BACKGROUND="black"
##POWERLEVEL9K_BATTERY_CHARGING_BACKGROUND="black"
##POWERLEVEL9K_BATTERY_CHARGED_BACKGROUND="black"
##POWERLEVEL9K_BATTERY_DISCONNECTED_BACKGROUND="black"
##POWERLEVEL9K_BATTERY_LOW_FOREGROUND="249"
##POWERLEVEL9K_BATTERY_CHARGING_FOREGROUND="249"
##POWERLEVEL9K_BATTERY_CHARGED_FOREGROUND="249"
##POWERLEVEL9K_BATTERY_DISCONNECTED_FOREGROUND="249"
##POWERLEVEL9K_BATTERY_LOW_VISUAL_IDENTIFIER_COLOR="red"
##POWERLEVEL9K_BATTERY_CHARGING_VISUAL_IDENTIFIER_COLOR="yellow"
##POWERLEVEL9K_BATTERY_CHARGED_VISUAL_IDENTIFIER_COLOR="green"
##POWERLEVEL9K_BATTERY_DISCONNECTED_VISUAL_IDENTIFIER_COLOR="249"
##POWERLEVEL9K_TIME_BACKGROUND="black"
##POWERLEVEL9K_TIME_FOREGROUND="249"
##POWERLEVEL9K_TIME_FORMAT="%D{%H:%M:%S}"
##### custom command
##POWERLEVEL9K_CUSTOM_WIFI_SIGNAL="zsh_wifi_signal"
##POWERLEVEL9K_CUSTOM_WIFI_SIGNAL_BACKGROUND="black"
##POWERLEVEL9K_CUSTOM_WIFI_SIGNAL_FOREGROUND="black"
##POWERLEVEL9K_CUSTOM_BATTERY_SIGNAL="zsh_battery_charge"
##POWERLEVEL9K_CUSTOM_BATTERY_SIGNAL_BACKGROUND="black"
##POWERLEVEL9K_CUSTOM_BATTERY_SIGNAL_FOREGROUND="249"
##### prompt line setting
##POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=('os_icon' 'todo' 'context' 'dir' 'vcs')
##POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=('status' 'custom_wifi_signal' 'battery' 'time')
##POWERLEVEL9K_MULTILINE_SECOND_PROMPT_PREFIX="╰─➢ "
##
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
