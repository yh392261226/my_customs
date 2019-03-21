# Desc: 最简化 终端主题
function miniprompt() {
    unset PROMPT_COMMAND
    PS1="\[\e[38;5;168m\]> \[\e[0m\]"
}