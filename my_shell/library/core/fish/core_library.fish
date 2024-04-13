set MYRUNTIME (cat $HOME/.myruntime)
set LIBRARYPATH $MYRUNTIME/customs/my_shell/library
set FUNCPATH $LIBRARYPATH/functions/fish
set COREPATH $LIBRARYPATH/core/fish
set THIRDPATH $LIBRARYPATH/third/fish
set OTHERSPATH $LIBRARYPATH/others/fish

# functions
if test -d $FUNCPATH
    for func in (ls $FUNCPATH/func_*.fish)
        source $func
    end
end

# cores
source $COREPATH/core_basic.fish
source $COREPATH/core_common.fish
source $COREPATH/core_export.fish
source $COREPATH/core_alias.fish
source $COREPATH/core_proxy.fish
source $COREPATH/core_ser.fish
source $COREPATH/core_other.fish

# thirds
if test -d $THIRDPATH
    for third in (ls $THIRDPATH/third_*.fish)
        source $third
    end
end

# others
if test -d $OTHERSPATH
    for other in (ls $OTHERSPATH/others_*.fish)
        source $other
    end
end
