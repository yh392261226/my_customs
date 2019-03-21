# Desc: Search for a file using MacOS Spotlight's metadata
function spotlight () { mdfind "kMDItemDisplayName == '$@'wc"; }