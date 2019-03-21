MYRUNTIME=$(cat $HOME/.myruntime)
for func in $(ls $MYRUNTIME/customs/my_shell/library/functions/*.sh); do
    source $func
done