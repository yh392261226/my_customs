# Desc: Flush dns
function flushdns() {
    sudo dscacheutil -flushcache
}