# Desc: 查找当前目录中包含某个字符串的
function mqfind () {
  find . -exec grep -l -s $1 {} \;
  return 0
}