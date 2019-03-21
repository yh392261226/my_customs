#   mans:   Search manpage given in agument '1' for term given in argument '2' (case insensitive)
#           displays paginated result with colored search terms and two lines surrounding each hit.             Example: mans mplayer codec
#   --------------------------------------------------------------------

# Desc: man command[$1] and highlight keyword[$2]
function mans () {
    man $1 | grep -iC2 --color=always $2 | less
}