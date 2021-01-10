MYRUNTIME=$(cat $HOME/.myruntime)
for func in $(ls $MYRUNTIME/customs/my_shell/library/functions/func_*.sh); do
    source $func
done

for core in $(ls $MYRUNTIME/customs/my_shell/library/core/core_*.sh); do
    source $core
done

for third in $(ls $MYRUNTIME/customs/my_shell/library/third/third_*.sh); do
    source $third
done