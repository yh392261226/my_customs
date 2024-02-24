# zoxide init fish | source
### fuck
#thefuck --alias | source
if test -d $HOME/.runtime/customs/others/fzf-help
  source $HOME/.runtime/customs/others/fzf-help/src/fzf-help.fish
  bind \ca fzf-help-widget
end
