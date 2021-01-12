# Desc: 自动检测文件后缀并 自动解压
extract () {
	if [ -f $1 ]
	then
		case $1 in
			(*.tar.bz2) tar xjf $1 ;;
			(*.tar.gz) tar xzf $1 ;;
			(*.tar.xz) tar xvf $1 ;;
			(*.bz2) bunzip2 $1 ;;
			(*.rar) unrar e $1 ;;
			(*.gz) gunzip $1 ;;
			(*.tar) tar xf $1 ;;
			(*.tbz2) tar xjf $1 ;;
			(*.tgz) tar xzf $1 ;;
			(*.zip) unzip $1 ;;
			(*.Z) uncompress $1 ;;
			(*.7z) 7z x $1 ;;
			(*) echo "'$1' cannot be extracted via extract()" ;;
		esac
	else
		echo "'$1' is not a valid file"
	fi
}

# Desc: 压缩目录为zip文件
function zipf () { zip -r "$1".zip "$1" ; }          # zipf:         To create a ZIP archive of a folder

# Desc: git压缩HEAD版本为zip包
function gitzip() {
    git archive -o $(basename $PWD).zip HEAD
}

# Desc: git压缩HEAD版本为tgz包
function gittgz() {
    git archive -o $(basename $PWD).tgz HEAD
}