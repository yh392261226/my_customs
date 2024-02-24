### enhancd / ecd
if ! set -q ENHANCD_ROOT; set -gx ENHANCD_ROOT "$HOME/.runtime/customs/others/enhancd/$name"; end
set -gx ENHANCD_COMMAND "ecd"
set -gx ENHANCD_DIR "$HOME/.enhancd"
set -gx ENHANCD_HOOK_AFTER_CD "lsd -l"
set -gx ENHANCD_USE_FUZZY_MATCH "1"
set -gx ENHANCD_COMPLETION_KEYBIND "^I"
set -gx ENHANCD_COMPLETION_BEHAVIOR "default"
set -gx ENHANCD_FILTER "/opt/homebrew/bin/peco:fzf:non-existing-filter"
