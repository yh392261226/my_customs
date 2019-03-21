# fzf (https://github.com/junegunn/fzf)
# --------------------------------------------------------------------

# Desc: cd to selected directory
function fd() {
    DIR=`find ${1:-*} -path '*/\.*' -prune -o -type d -print 2> /dev/null | fzf-tmux` \
        && cd "$DIR"
}