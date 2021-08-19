###
# Url: https://github.com/zdharma/zini
# Desc: zsh的管理插件 据说效率很高
###
if [ -f $MYRUNTIME/customs/others/zinit/zinit.zsh ]; then
    source $MYRUNTIME/customs/others/zinit/zinit.zsh
    autoload -Uz _zinit
    (( ${+_comps} )) && _comps[zinit]=_zinit

    # zinit load  <repo/plugin> # Load with reporting/investigating.
    # zinit light <repo/plugin> # Load without reporting/investigating.
    # zinit snippet <URL>
    zinit light zdharma/fast-syntax-highlighting
    # zinit snippet https://gist.githubusercontent.com/hightemp/5071909/raw/
fi