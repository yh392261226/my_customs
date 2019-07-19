#!/usr/bin/env bash
# ➳
### PS头
# if [ "$PLATFORM" = Linux ]; then
# 	PS1="\[\e[1;38m\]\u\[\e[1;34m\]@\[\e[1;31m\]\h\[\e[1;30m\]:"
# 	PS1="$PS1\[\e[0;38m\]\w\[\e[1;35m\]> \[\e[0m\]"
# else
# 	### git-prompt
# 	__git_ps1() { :;}
# 	if [ -e ~/.git-prompt.sh ]; then
# 		source ~/.git-prompt.sh
# 	fi
# 	# PROMPT_COMMAND='history -a; history -c; history -r; printf "\[\e[38;5;59m\]%$(($COLUMNS - 4))s\r" "$(__git_ps1) ($(date +%m/%d\ %H:%M:%S))"'
# 	PROMPT_COMMAND='history -a; printf "\[\e[38;5;59m\]%$(($COLUMNS - 4))s\r" "$(__git_ps1) ($(date +%m/%d\ %H:%M:%S))"'
# 	PS1="\[\e[34m\]\u\[\e[1;32m\]@\[\e[0;33m\]\h\[\e[35m\]:"
# 	PS1="$PS1\[\e[m\]\w\[\e[1;31m\]> \[\e[0m\]"
# fi
