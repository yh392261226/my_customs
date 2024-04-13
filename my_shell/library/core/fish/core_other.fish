set is_notify 0

# export 设定
if test -d $HOME/.nvm
    set -x NVM_DIR $HOME/.nvm
end

# source 引入
# nvm
if test -s "$HOME/.nvm/nvm.sh"
    source $HOME/.nvm/nvm.sh
end
if test -s "$NVM_DIR/nvm.sh"
    source "$NVM_DIR/nvm.sh"
end
if test -f $HOME/.rvm/scripts/rvm
    source $HOME/.rvm/scripts/rvm
end
if test -s $HOME/.autojump/etc/profile.d/autojump.sh
    source $HOME/.autojump/etc/profile.d/autojump.sh
end
if test -f $HOME/.fzf.fish
    source $HOME/.fzf.fish
end
if test -d /usr/local/opt/sphinx-doc/bin
    set -x PATH /usr/local/opt/sphinx-doc/bin $PATH
end
if test -d /opt/homebrew/opt/sphinx-doc/bin
    set -x PATH /opt/homebrew/opt/sphinx-doc/bin $PATH
end
if test -d /usr/local/opt/openssl/lib
    set -x LDFLAGS "-L/usr/local/opt/openssl/lib"
end
if test -d /opt/homebrew/opt/openssl/lib
    set -x LDFLAGS "-L/opt/homebrew/opt/openssl/lib"
end
if test -d /usr/local/opt/openssl/include
    set -x CPPFLAGS "-I/usr/local/opt/openssl/include"
end
if test -d /opt/homebrew/opt/openssl/include
    set -x CPPFLAGS "-I/opt/homebrew/opt/openssl/include"
end

# vim&nvim remote
if test -f $HOME/.SpaceVim -o -d $HOME/.SpaceVim
    set -x PATH $HOME/.SpaceVim/bin $PATH
end

if test -d $HOME/.yarn/bin
    set -x PATH $HOME/.yarn/bin $PATH
end
if test -d $HOME/.local/bin
    set -x PATH $HOME/.local/bin $PATH
end

# iterm2 shell integration
if test -e $HOME/.iterm2_shell_integration.fish
    source $HOME/.iterm2_shell_integration.fish
end

set is_notify 0

if test -f /opt/homebrew/bin/pokemon
    alias ding "/opt/homebrew/bin/pokemon"
end
if test -f /usr/local/bin/pokemon
    alias ding "/usr/local/bin/pokemon"
end

if test $is_notify -gt 0
    echo "Please Restart a new terminal window to effect the changing !!!"
end

# Bashhub.com Installation
if not test -d $HOME/.bashhub/
    curl -OL https://bashhub.com/setup; and fish setup
end

if not command -v atuin > /dev/null 2>&1
    brew install atuin
end

# SSH config && tmp directory
if not test -f $HOME/.ssh/config
    ln -sf $MYRUNTIME/customs/customs_modify_records/ssh_config $HOME/.ssh/config
end
if not test -d $HOME/.ssh/tmp
    mkdir -p $HOME/.ssh/tmp
end


# _lessfilter
if test -f $MYRUNTIME/customs/bin/_lessfilter
    if not test -f $HOME/.lessfilter
        ln -sf $MYRUNTIME/customs/bin/_lessfilter $HOME/.lessfilter
    end
end

# zoxide
if test "" != (brew --prefix zoxide)
    eval (zoxide init fish)
end

if test -d /opt/homebrew/opt/ssh-copy-id/bin
    set -x PATH /opt/homebrew/opt/ssh-copy-id/bin $PATH
end
if test -d /usr/local/opt/ssh-copy-id/bin
    set -x PATH /opt/homebrew/opt/ssh-copy-id/bin $PATH
end

# custom commands
# fasd
# fasd --init auto | source
# the fuck command
#eval (thefuck --alias)
# the aliases command
# aliases init --global | source
# the atuin import
atuin init fish | source

# fzf
# Set up fzf key bindings and fuzzy completion
fzf --fish | source

# Git configs
git config --global alias.co checkout
git config --global alias.ci commit
git config --global alias.cm commit
git config --global alias.st status
git config --global alias.ad add
git config --global alias.df diff
git config --global alias.dfc "diff --cached"
git config --global alias.br branch
git config --global alias.lol "log --graph --decorate --pretty=oneline --abbrev-commit"
git config --global alias.lola "log --graph --decorate --pretty=oneline --abbrev-commit --all"
git config --global alias.subup "submodule update --init --recursive"
git config --global alias.subst "submodule status --recursive"

set default_user (/usr/bin/whoami)
/bin/sh $MYRUNTIME/customs/bin/extendslocatetochangepicurl
if test -f $MYRUNTIME/customs/bin/start
    $MYRUNTIME/customs/bin/start
end

# Dotbare
set -x DOTBARE_DIR "$HOME/.cfg"
set -x DOTBARE_TREE "$HOME"
alias config dotbare

# enhancd / ecd
if ! set -q ENHANCD_ROOT; set -gx ENHANCD_ROOT "$MYRUNTIME/customs/others/enhancd/$name"; end
set -gx ENHANCD_COMMAND "ecd"
set -gx ENHANCD_DIR "$HOME/.enhancd"
set -gx ENHANCD_HOOK_AFTER_CD "lsd -l"
set -gx ENHANCD_USE_FUZZY_MATCH "1"
set -gx ENHANCD_COMPLETION_KEYBIND "^I"
set -gx ENHANCD_COMPLETION_BEHAVIOR "default"
set -gx ENHANCD_FILTER "/opt/homebrew/bin/peco:fzf:non-existing-filter"

# fzf-help
if test -d $MYRUNTIME/customs/others/fzf-help
  source $MYRUNTIME/customs/others/fzf-help/src/fzf-help.fish
  bind \ca fzf-help-widget
end

# forgit
if test -d $HOME/.zinit/plugins/wfxr---forgit/conf.d; and test -f $HOME/.zinit/plugins/wfxr---forgit/conf.d/forgit.plugin.fish
    if not test -f $HOME/.config/fish/conf.d/forgit.fish
        ln -sf $HOME/.zinit/plugins/wfxr---forgit/conf.d/forgit.plugin.fish $HOME/.config/fish/conf.d/forgit.fish
    end
end

# Homebrew
set -x HOMEBREW_NO_AUTO_UPDATE 1