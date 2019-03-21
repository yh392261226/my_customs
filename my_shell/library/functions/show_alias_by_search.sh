# Desc: 显示所有含有字符串的自定义命令及注释
function showa () {
    MYRUNTIME=$(cat $HOME/.myruntime)
    customcd $MYRUNTIME/customs/my_shell/library/functions; find *.sh | xargs ag "$1" | awk -F':' '{print $1}' | fzf  --no-sort --tac --toggle-sort=ctrl-r --height 95% --reverse --preview 'cat {}' --preview-window right:140
    # grep --color=always -i -a2 $@ $MYRUNTIME/customs/my_shell/my_alias.sh $MYRUNTIME/customs/my_shell/my_func.sh | grep -v '^\s*$' | less -FSRXc ;
}