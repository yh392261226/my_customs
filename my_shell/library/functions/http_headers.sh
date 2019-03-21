# Desc: Grabs headers from web page
function httpHeaders () { curl -I -L $@ ; }