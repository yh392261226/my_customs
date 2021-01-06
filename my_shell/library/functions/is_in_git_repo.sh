# Desc: pick files from `git status -s`
function isgit() {
  git rev-parse HEAD > /dev/null 2>&1
}