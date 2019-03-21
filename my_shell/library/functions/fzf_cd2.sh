# Desc: cdff - cd into the directory of the selected file
function cdff() {
   local file
   local dir
   file=$(fzf +m -q "$1") && dir=$(dirname "$file") && cd "$dir"
}