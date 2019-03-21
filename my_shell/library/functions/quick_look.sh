# Desc: Opens any file in MacOS Quicklook Preview
function ql () { qlmanage -p "$*" >& /dev/null; }    # ql:           Opens any file in MacOS Quicklook Preview