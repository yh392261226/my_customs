# Desc: Always list directory contents upon 'cd'
function cd() { builtin cd "$@"; /bin/ls -aGH; }  