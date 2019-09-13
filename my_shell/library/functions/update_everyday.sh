# Desc: 每天一更新
function upday() {
    upruntimes
    upzshcustoms
    #upzshcustoms
    brew update  && brew upgrade && brew cleanup
    gethosts
}
