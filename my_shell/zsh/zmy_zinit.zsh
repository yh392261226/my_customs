###
# Url: https://github.com/zdharma/zini
# Desc: zsh的管理插件 据说效率很高
# # 加载插件
# zinit load {plg-spec}

# 加载插件，不打印加载信息
# zinit light [-b] {plg-spec}

# 加载单文件，-f 表示不使用缓存，即强制重新下载
# zinit snippet [-f] {url}

# 卸载插件，-q 表示 quiet
# zinit unload [-q] {plg-spec}

# 显示插件加载时间，以插件加载顺序排序。-s 表示以秒进行显示（默认毫秒），-m 表示显示插件加载时刻
# zinit times [-s] [-m]

# 显示 Zinit 状态
# zinit zstatus

# 显示插件加载状态，--all 表示显示所有插件
# zinit report {plg-spec} | --all

# 显示已加载的插件（使用关键字进行过滤）
# zinit loaded [keyword],list [keyword]

# 显示每个插件的设置的按键绑定
# zinit bindkeys

# 编译插件
# zinit compile {plg-spec} | --all

# 移除已编译的插件
# zinit uncompile {plg-spec} | --all

# 显示已编译的插件
# zinit compiled

# 更新 Zinit
# zinit self-update

# 更新插件/脚本，--all 表示更新所有插件/脚本，-q 表示静默更新，-r | --reset 更新前执行 git reset --hard / svn revert
# zinit update [-q] [-r] {plg-spec} | URL | --all

# 为下一条 zinit 命令添加 ice 描述符
# zinit ice <ice specification>

# 磁盘删除插件/脚本，--all 表示清除，--clean 表示删除未加载的插件/脚本
# zinit delete {plg-spec} | URL | --clean | --all

# 进入插件目录
# zinit cd {plg-spec}
###
if [ -f $MYRUNTIME/customs/others/zinit/zinit.zsh ]; then
    source $MYRUNTIME/customs/others/zinit/zinit.zsh
    autoload -Uz _zinit
    (( ${+_comps} )) && _comps[zinit]=_zinit

    # zinit load  <repo/plugin> # Load with reporting/investigating.
    # zinit light <repo/plugin> # Load without reporting/investigating.
    # zinit snippet <URL>
    # zinit snippet https://gist.githubusercontent.com/hightemp/5071909/raw/
#=============================================================================

    ###Customs
    zinit ice lucid wait='0'

    # 加载 OMZ 框架及部分插件
    # zinit snippet OMZL::git.zsh
    zinit snippet OMZL::history.zsh
    zinit snippet OMZL::key-bindings.zsh
    zinit snippet OMZL::clipboard.zsh
    zinit snippet OMZL::completion.zsh
    zinit snippet OMZL::theme-and-appearance.zsh

    zinit snippet OMZP::cp
    zinit snippet OMZP::brew
    # zinit snippet OMZP::vi-mode
    zinit snippet OMZP::sublime
    zinit snippet OMZP::gitignore
    zinit snippet OMZP::colored-man-pages
    # zinit snippet OMZP::git/git.plugin.zsh
    # zinit snippet OMZP::mvn/mvn.plugin.zsh
    zinit snippet OMZP::sudo/sudo.plugin.zsh
    # zinit snippet OMZP::common-aliases/common-aliases.plugin.zsh
    # zinit snippet OMZP::colored-man-pages/colored-man-pages.plugin.zsh
    # zinit snippet OMZP::extract
    zinit snippet OMZP::pip/pip.plugin.zsh
    zinit snippet OMZP::command-not-found/command-not-found.plugin.zsh
    # zinit snippet OMZP::tmux/tmux.plugin.zsh
    zinit snippet https://gist.githubusercontent.com/Hill-98/93db00b01327a0226955c2c6b3b7e137/raw/auto-bin-path.zsh

    # 延迟加载
    zinit ice lucid wait='3'
    # 快速目录跳转
    zinit light skywind3000/z.lua
    zinit light zsh-users/zsh-completions
    zinit light zsh-users/zsh-autosuggestions
    zinit light zdharma-continuum/fast-syntax-highlighting
    # zinit light changyuheng/zsh-interactive-cd
    zinit light shengyou/codeception-zsh-plugin
    zinit light zsh-users/zsh-syntax-highlighting
    zinit light paoloantinori/hhighlighter
    zinit light floor114/zsh-apple-touchbar
    zinit light djui/alias-tips
    zinit light zsh-users/zsh-history-substring-search
    zinit light iam4x/zsh-iterm-touchbar
    zinit light supercrabtree/k
    zinit light wfxr/formarks
    zinit light junegunn/fzf
    zinit light chitoku-k/fzf-zsh-completions
    zinit light amaya382/zsh-fzf-widgets
    zinit light urbainvaes/fzf-marks
    zinit light Aloxaf/fzf-tab
    zinit light edouard-lopez/yeoman-zsh-plugin
    zinit light yh392261226/git-extra-commands
    zinit light horosgrisa/mysql-colorize
    zinit light zdharma-continuum/zbrowse
    zinit light zdharma-continuum/zui
    zinit light kazhala/dotbare
    zinit light wfxr/forgit
    zinit light paulirish/git-open
    zinit light thirteen37/fzf-brew

    # ASDF
    if [ -d "$HOME/.asdf" ]; then
        zinit ice wait lucid
        zinit light asdf-vm/asdf
    else
        mkdir $HOME/.asdf
    fi

    function reload_zinit() {
        source $MYRUNTIME/customs/my_shell/zsh/zmy_zinit.zsh
    }
    alias reloadz="reload_zinit"


    zinit ice lucid wait='2'
    zinit ice svn
    zinit ice depth=1; zinit light romkatv/powerlevel10k
fi

#bindkey ',' autosuggest-accept
