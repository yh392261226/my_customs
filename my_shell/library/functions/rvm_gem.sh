# Desc: rvm多个版本的gem操作同一个包
function gems() {
    for v in 2.0.0 1.8.7 jruby 1.9.3; do
        rvm use $v
        gem $@
    done
}