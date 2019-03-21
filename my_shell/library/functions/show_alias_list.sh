# Desc: 显示所有自定义命令及注释
function showaliases() {
    MYRUNTIME=$(cat $HOME/.myruntime)
    customcd $MYRUNTIME/customs/my_shell/library/functions; ls *.sh| fzf --no-sort --tac --toggle-sort=ctrl-r --height 95% --reverse --preview 'cat {}' --preview-window right:140
    # touch /tmp/tmp_all_aliases.log
    # for file in $(ls $MYRUNTIME/customs/my_shell/library/functions/*.sh); do
    #     cat $file | grep '^function ' | awk '{print "Command: " $2}' | sed 's/()//' | sed 's/{//' >> /tmp/tmp_all_aliases.log
    #     cat $file | grep 'Desc:' | sed 's/#//' | sed 's/[ ][ ]*//' >> /tmp/tmp_all_aliases.log
    #     echo '---------------------------------------------------' >> /tmp/tmp_all_aliases.log
    # done
    # if [ -f /tmp/tmp_all_aliases.log ]; then
    #     cat /tmp/tmp_all_aliases.log | fzf --no-sort --tac --toggle-sort=ctrl-r --height 40% --reverse --preview 'cat {}' --preview-window right:140
    #     # rm -f /tmp/tmp_all_aliases.log
    # fi
}



