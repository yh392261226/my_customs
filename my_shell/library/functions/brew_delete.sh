# Desc: Brew Delete (one or multiple) selected application(s)
# mnemonic (e.g. uninstall)
function bdl() {
  local uninst=$(brew leaves | fzf -m)

  if [[ $uninst ]]; then
    for prog in $(echo $uninst); do
        brew uninstall $prog; 
    done;
  fi
}