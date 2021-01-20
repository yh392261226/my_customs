function zsh_wifi_signal() { # Desc: zsh获取WiFi网速
    if [ "$MYSYSNAME" = "Mac" ]; then
        local output=$(/System/Library/PrivateFrameworks/Apple80211.framework/Versions/A/Resources/airport -I)
        local airport=$(echo $output | grep 'AirPort' | awk -F': ' '{print $2}')

        if [ "$airport" = "Off" ]; then
                local color='%F{yellow}'
                echo -n "%{$color%}Wifi Off"
        else
                local ssid=$(echo $output | grep ' SSID' | awk -F': ' '{print $2}')
                local speed=$(echo $output | grep 'lastTxRate' | awk -F': ' '{print $2}')
                local color='%F{yellow}'

                [[ $speed -gt 100 ]] && color='%F{green}'
                [[ $speed -lt 50 ]] && color='%F{red}'

                echo -n "%{$color%}WIFI:$ssid SPEED:$speed Mb/s%{%f%}" # removed char not in my PowerLine font
        fi
    elif [ "$MYSYSNAME" = "Centos" ] || [ "$MYSYSNAME" = "Ubuntu" ]; then
        local signal=$(nmcli device wifi | grep yes | awk '{print $8}')
        local color='%F{yellow}'
        [[ $signal -gt 75 ]] && color='%F{green}'
        [[ $signal -lt 50 ]] && color='%F{red}'
        echo -n "%{$color%}\uf230  $signal%{%f%}" # \uf230 is 
    fi
}

function zsh_battery_charge { # Desc: zsh电池图
    echo `~/bin/battery.py`
}