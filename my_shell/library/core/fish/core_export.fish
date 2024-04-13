# 环境变量设定
set -x PLATFORM (uname -s)
set -x BASE $HOME

if test -d /usr/local/opt/macvim
    set -x PATH /usr/local/opt/macvim/bin /usr/local/bin $PATH
end

if test -d /opt/homebrew/opt/macvim
    set -x PATH /opt/homebrew/opt/macvim/bin /usr/local/bin $PATH
end

if test -d /usr/local/var/rbenv
    set -x RBENV_ROOT /usr/local/var/rbenv
    rbenv init -
end

if test -d /usr/local/opt/python
    set -x PATH /usr/local/opt/python/bin $PATH
end

if test -d /opt/homebrew/opt/python
    set -x PATH /opt/homebrew/opt/python/bin $PATH
end

if test -d /usr/local/opt/python@2/libexec/bin
    set -x PATH /usr/local/opt/python@2/libexec/bin $PATH
end

if test -f $HOME/.cargo/env
    set -x PATH $HOME/.cargo/bin $PATH
end

if test -d /opt/local/bin
    set -x PATH /opt/local/bin $PATH
end

if test -d $HOME/.local/bin
    set -x PATH $HOME/.local/bin $PATH
end

if test -d $HOME/.yarn/bin
    set -x PATH $HOME/.yarn/bin $PATH
end

if test -d $HOME/.SpaceVim/bin
    set -x PATH $HOME/.SpaceVim/bin $PATH
end

if test -d /opt/homebrew/opt/sphinx-doc/bin
    set -x PATH /opt/homebrew/opt/sphinx-doc/bin $PATH
end


# if test -d /usr/local/opt/pyenv
#     set -x PYENV_ROOT /usr/local/var/pyenv
#     set -x PATH $PYENV_ROOT/bin $PATH
#     pyenv init -
# end

# if test -d /opt/homebrew/opt/pyenv
#     pyenv init -
# end

# if which pyenv-virtualenv-init > /dev/null
#     pyenv virtualenv-init -
# end

# 设置PATH变量
if test "$MYSYSNAME" = "Mac"
    if test -d /usr/bin
        set -x PATH /usr/bin $PATH
    end

    if test -d /bin
        set -x PATH /bin $PATH
    end

    if test -d /usr/sbin
        set -x PATH /usr/sbin $PATH
    end

    if test -d /sbin
        set -x PATH /sbin $PATH
    end

    if test -d /usr/local/bin
        set -x PATH /usr/local/bin $PATH
    end

    if test -d /usr/local/sbin
        set -x PATH /usr/local/sbin $PATH
    end

    if test -d /usr/local/var/rbenv/shims
        set -x PATH /usr/local/var/rbenv/shims $PATH
    end

    if test -d $HOME/go/bin
        set -x PATH $HOME/go/bin $PATH
    end

    if test -d $HOME/.cabal/bin
        set -x PATH $HOME/.cabal/bin $PATH
    end

    if test -d $HOME/bin
        set -x PATH $HOME/bin $PATH
    end

    if test -d /usr/local/opt/go/bin
        set -x PATH /usr/local/opt/go/bin $PATH
    end

    if test -d /usr/local/heroku/bin
        set -x PATH /usr/local/heroku/bin $PATH
    end

    if test -d $MYRUNTIME/customs/bin
        set -x PATH $MYRUNTIME/customs/bin $PATH
    end

    if test -d /usr/local/opt/llvm/bin
        set -x PATH /usr/local/opt/llvm/bin $PATH
    end

    if test -d /usr/local/opt/coreutils/libexec/gnubin
        set -x PATH /usr/local/opt/coreutils/libexec/gnubin $PATH
    end

    if test -d $HOME/.Pokemon-Terminal
        set -x PATH $HOME/.Pokemon-Terminal $PATH
    end

    if test -d /usr/local/anaconda3/bin
        set -x PATH /usr/local/anaconda3/bin/ $PATH
    end

    if test -d /opt/homebrew/bin
        set -x PATH /opt/homebrew/bin $PATH
    end

    if test -d /opt/homebrew/sbin
        set -x PATH /opt/homebrew/sbin $PATH
    end

    if test -d /opt/homebrew/opt/grep/bin
        set -x PATH /opt/homebrew/opt/grep/bin $PATH
    end

    if test -d /opt/homebrew/opt/icu4c/bin
        set -x PATH /opt/homebrew/opt/icu4c/bin $PATH
    end

    if test -d /opt/homebrew/opt/llvm@15/bin
        set -x PATH /opt/homebrew/opt/llvm@15/bin $PATH
    end

    if test -d /opt/homebrew/opt/ed/bin
        set -x PATH /opt/homebrew/opt/ed/bin $PATH
    end

    if test -d /Library/Apple/usr/bin
        set -x PATH /Library/Apple/usr/bin $PATH
    end

    if test -d /opt/homebrew/opt/fzf/bin
        set -x PATH /opt/homebrew/opt/fzf/bin $PATH
    end

    if test -d /usr/local/opt/fzf/bin
        set -x PATH /usr/local/opt/fzf/bin $PATH
    end
else
    set -x PATH /usr/local/rvm/bin $HOME/.cabal/bin /sbin /bin /usr/sbin /usr/bin /usr/local/bin /usr/local/sbin $PATH
end

set -gx PATH $MYRUNTIME/customs/bin $PATH
set -gx PATH $MYRUNTIME/customs/bin/ssh-auto-login/auto_gen $PATH

# 设置editor
if test "$MYSYSNAME" = "Mac"
    if test -f /usr/local/bin/code
        set -x EDITOR /usr/local/bin/code
    else
        set -x EDITOR "nvim"
    end
else if test "$MYSYSNAME" = "Ubuntu" || test "$MYSYSNAME" = "Centos"
    set -x EDITOR "gedit"
end

if test -d $HOME/.basher
    set -x PATH $HOME/.basher/bin $PATH
    basher init -
end

# M1 sqlite3
if test -d /opt/homebrew/opt/sqlite/bin
    set -x PATH /opt/homebrew/opt/sqlite/bin $PATH
    set -x LDFLAGS "-L/opt/homebrew/opt/sqlite/lib"
    set -x CPPFLAGS "-I/opt/homebrew/opt/sqlite/include"
    set -x PKG_CONFIG_PATH "/opt/homebrew/opt/sqlite/lib/pkgconfig"
end

# wine 不输出debug信息
set -x WINEDEBUG -all
set -x MYCUSTOMS $MYRUNTIME/customs
set -x MYTOOLS $MYRUNTIME/tools
set -x MYSHELL $MYCUSTOMS/my_shell
set -x MYBIN $MYCUSTOMS/bin

# fzf-dirhistory
set -x DIR_HISTORY_FILE $HOME/.fzf_dirhistory
set -x DIR_HISTORY_SIZE 2000

# Git
set -x GIT_MERGE_AUTOEDIT no  # while git pull does not open merge editor
