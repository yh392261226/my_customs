# Desc: short for cdfinder
function mcdf () {
  cd "`osascript -e 'tell app "Finder" to POSIX path of (insertion location as alias)'`"
}