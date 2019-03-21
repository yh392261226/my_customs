# Desc: git压缩HEAD版本为tgz包
function gittgz() {
    git archive -o $(basename $PWD).tgz HEAD
}