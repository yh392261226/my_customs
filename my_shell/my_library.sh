MYRUNTIME=$(cat $HOME/.myruntime)
for func in $(ls $MYRUNTIME/customs/my_shell/library/functions/bzsh/func_*.bzsh); do
    source $func
done

for core in $(ls $MYRUNTIME/customs/my_shell/library/core/bzsh/core_*.bzsh); do
    source $core
done

for third in $(ls $MYRUNTIME/customs/my_shell/library/third/bzsh/third_*.bzsh); do
    source $third
done

for other in $(ls $MYRUNTIME/customs/my_shell/library/others/bzsh/others_*.bzsh); do
    source $other
done
