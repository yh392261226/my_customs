set Color_off '\033[0m'       # Text Reset

# terminal color template
# Regular Colors
set Black '\033[0;30m'        # Black
set Red '\033[0;31m'          # Red
set Green '\033[0;32m'        # Green
set Yellow '\033[0;33m'       # Yellow
set Blue '\033[0;34m'         # Blue
set Purple '\033[0;35m'       # Purple
set Cyan '\033[0;36m'         # Cyan
set White '\033[0;37m'        # White

# Bold
set BBlack '\033[1;30m'       # Black
set BRed '\033[1;31m'         # Red
set BGreen '\033[1;32m'       # Green
set BYellow '\033[1;33m'      # Yellow
set BBlue '\033[1;34m'        # Blue
set BPurple '\033[1;35m'      # Purple
set BCyan '\033[1;36m'        # Cyan
set BWhite '\033[1;37m'       # White

# Underline
set UBlack '\033[4;30m'       # Black
set URed '\033[4;31m'         # Red
set UGreen '\033[4;32m'       # Green
set UYellow '\033[4;33m'      # Yellow
set UBlue '\033[4;34m'        # Blue
set UPurple '\033[4;35m'      # Purple
set UCyan '\033[4;36m'        # Cyan
set UWhite '\033[4;37m'       # White

# Background
set On_Black '\033[40m'       # Black
set On_Red '\033[41m'         # Red
set On_Green '\033[42m'       # Green
set On_Yellow '\033[43m'      # Yellow
set On_Blue '\033[44m'        # Blue
set On_Purple '\033[45m'      # Purple
set On_Cyan '\033[46m'        # Cyan
set On_White '\033[47m'       # White

# High Intensity
set IBlack '\033[0;90m'       # Black
set IRed '\033[0;91m'         # Red
set IGreen '\033[0;92m'       # Green
set IYellow '\033[0;93m'      # Yellow
set IBlue '\033[0;94m'        # Blue
set IPurple '\033[0;95m'      # Purple
set ICyan '\033[0;96m'        # Cyan
set IWhite '\033[0;97m'       # White

# Bold High Intensity
set BIBlack '\033[1;90m'      # Black
set BIRed '\033[1;91m'        # Red
set BIGreen '\033[1;92m'      # Green
set BIYellow '\033[1;93m'     # Yellow
set BIBlue '\033[1;94m'       # Blue
set BIPurple '\033[1;95m'     # Purple
set BICyan '\033[1;96m'       # Cyan
set BIWhite '\033[1;97m'      # White

# High Intensity backgrounds
set On_IBlack '\033[0;100m'   # Black
set On_IRed '\033[0;101m'     # Red
set On_IGreen '\033[0;102m'   # Green
set On_IYellow '\033[0;103m'  # Yellow
set On_IBlue '\033[0;104m'    # Blue
set On_IPurple '\033[0;105m'  # Purple
set On_ICyan '\033[0;106m'    # Cyan
set On_IWhite '\033[0;107m'   # White

# success/info/error/warn
function msg
    printf '%b\n' "$argv[1]" >&2
end

function success
    msg "$Green[✔]$Color_off $argv[1]$argv[2]"
    return 0
end

function info
    msg "$Blue[➭]$Color_off $argv[1]$argv[2]"
    return 0
end

function error
    msg "$Red[✘]$Color_off $argv[1]$argv[2]"
    return 1
end

function warn
    msg "$Yellow[⚠]$Color_off $argv[1]$argv[2]"
end

# echo_with_color
function echo_with_color
    printf '%b\n' "$argv[1]$argv[2]$Color_off" >&2
end

function ifHasCommand
    if not command -v $argv[1] >/dev/null 2>&1
        echo "0"
    else
        echo "1"
    end
end
