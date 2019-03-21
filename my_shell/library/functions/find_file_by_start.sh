# Desc: Find file whose name starts with a given string
function ffs () { find . -name "$@"'*' ; }