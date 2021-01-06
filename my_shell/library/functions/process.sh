# Desc: List processes owned by my user:
function myps() { ps $@ -u $USER -o pid,%cpu,%mem,start,time,bsdtime,command ; }