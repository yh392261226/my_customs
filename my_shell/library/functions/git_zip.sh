# Desc: git压缩HEAD版本为zip包
function gitzip() {
    git archive -o $(basename $PWD).zip HEAD
}