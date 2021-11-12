function extract() { # Desc: extract:自动检测文件后缀并 自动解压
	if [ -z "$1" ]; then
    	echo "Usage: extract <path/file_name>.<zip|rar|bz2|gz|tar|tbz2|tgz|Z|7z|xz|ex|tar.bz2|tar.gz|tar.xz>"
	else
		if [ -f $1 ]; then
			case $1 in
				*.tar.bz2)   tar xvjf $1    ;;
				*.tar.gz)    tar xvzf $1    ;;
				*.tar.xz)    tar xvJf $1    ;;
				*.lzma)      unlzma $1      ;;
				*.bz2)       bunzip2 $1     ;;
				*.rar)       unrar x -ad $1 ;;
				*.gz)        gunzip $1      ;;
				*.tar)       tar xvf $1     ;;
				*.tbz2)      tar xvjf $1    ;;
				*.tgz)       tar xvzf $1    ;;
				*.zip)       unzip $1       ;;
				*.Z)         uncompress $1  ;;
				*.7z)        7z x $1        ;;
				*.xz)        unxz $1        ;;
				*.exe)       cabextract $1  ;;
				*)           echo "extract: '$1' - unknown archive method" ;;
			esac
		else
			echo "$1 - file does not exist"
		fi
	fi
}
alias extr='extract'

function abspath() {
    if [ -d "$1" ]; then
        echo "$(cd $1; pwd)"
    elif [ -f "$1" ]; then
        if [[ $1 == */* ]]; then
            echo "$(cd ${1%/*}; pwd)/${1##*/}"
        else
            echo "$(pwd)/$1"
        fi
    fi
}
alias abspath="abspath"

function free() {
    FREE_BLOCKS=$(vm_stat | grep free | awk '{ print $3 }' | sed 's/\.//')
    INACTIVE_BLOCKS=$(vm_stat | grep inactive | awk '{ print $3 }' | sed 's/\.//')
    SPECULATIVE_BLOCKS=$(vm_stat | grep speculative | awk '{ print $3 }' | sed 's/\.//')
    FREE=$((($FREE_BLOCKS+SPECULATIVE_BLOCKS)*4096/1048576))
    INACTIVE=$(($INACTIVE_BLOCKS*4096/1048576))
    TOTAL=$((($FREE+$INACTIVE)))
    echo "Free:       $FREE MB"
    echo "Inactive:   $INACTIVE MB"
    echo "Total free: $TOTAL MB"
}
alias free="free"

function compress_zip_file() { # Desc: compress_zip_file:压缩目录为zip文件
	zip -r "$1".zip "$1" ;
}
alias zipf="compress_zip_file"

function compress_git_to_zip() { # Desc: gitzip:git压缩HEAD版本为zip包
    git archive -o $(basename $PWD).zip HEAD
}
alias gitzip="compress_git_to_zip"

function compress_git_to_tgz() { # Desc: gittgz:git压缩HEAD版本为tgz包
    git archive -o $(basename $PWD).tgz HEAD
}
alias gittgz="compress_git_to_tgz"