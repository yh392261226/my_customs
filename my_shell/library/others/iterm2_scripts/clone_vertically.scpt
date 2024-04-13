tell application "iTerm2"
  tell current session of current window
    set tty_now to tty
    set clone_host to (do shell script "ps -o tty,command|grep $(echo " & tty_now & "|awk -F'/' '{print $3}')|grep '  ssh'|awk -F'  ' '{print $2}'")
    split vertically with default profile command clone_host
  end tell
end tell
