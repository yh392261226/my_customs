set -x LIGHT_THEME "Novel"
set -x DARK_THEME "Seafoam Pastel"

function toggle-theme
    # Desc: function: toggle-theme:更换iterm配置的主题
    echo "使用此命令会将iterm的配置更改，是否确认使用？ y/n"
    read -P "y/n" answer
    if test "$answer" = "y" -o "$answer" = "yes"
        python3 $MYRUNTIME/customs/others/iterm2-theme-toggle/main.py
    end
end

abbr -a tt toggle-theme # Desc: alias: tt: toggle-theme命令的别名

function change_iterm2_color_scheme
    # Desc: function: change_iterm2_color_scheme:更换iterm当前session的主题
    set act $argv[1]
    if test -z $act
        set act session
    end
    set theme $argv[2]
    if test -n $theme
        python3 $MYRUNTIME/customs/my_shell/library/others/iterm2_scripts/change_color.py $act $theme
    else
        python3 $MYRUNTIME/customs/my_shell/library/others/iterm2_scripts/change_color.py $act
    end
end

abbr -a cics change_iterm2_color_scheme # Desc: alias: cics: change_iterm2_color_scheme命令的别名
