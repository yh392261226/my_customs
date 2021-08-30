MYRUNTIME=$(cat $HOME/.myruntime)
for func in $(ls $MYRUNTIME/customs/my_shell/library/functions/func_*.bzsh); do
    source $func
done

for core in $(ls $MYRUNTIME/customs/my_shell/library/core/core_*.bzsh); do
    source $core
done

for third in $(ls $MYRUNTIME/customs/my_shell/library/third/third_*.bzsh); do
    source $third
done

for other in $(ls $MYRUNTIME/customs/my_shell/library/others/others_*.bzsh); do
    source $other
done