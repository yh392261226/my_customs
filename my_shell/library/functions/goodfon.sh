# Desc: open the website goodfon
function goodfon() {
    local DEFAULTBROWSER="/Applications/Firefox.app"      #default browser for open goodfon
    local SECONDBROWSER="/Applications/Google Chrome.app" #second browser for open goodfon
    local URL="https://www.goodfon.ru/"

    if [ "$1" = "" ]; then
        [[ -d "$DEFAULTBROWSER" ]] && /usr/bin/open -a "$DEFAULTBROWSER" "$URL"
    fi

    if [ "$1" = "chrome" ] || [ "$1" = "google" ]; then
        [[ -d "$SECONDBROWSER" ]] && /usr/bin/open -a "$SECONDBROWSER" "$URL"
    fi
}