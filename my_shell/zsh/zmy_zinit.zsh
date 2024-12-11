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
    zinit ice lucid wait='2'

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
    #zinit snippet https://gist.githubusercontent.com/Hill-98/93db00b01327a0226955c2c6b3b7e137/raw/auto-bin-path.zsh

    # 延迟加载
    zinit ice lucid wait='3'
    # 快速目录跳转
    zinit light skywind3000/z.lua
    # 自动补全
    # zinit light zsh-users/zsh-completions
    # 根据输入进行命令预测
    zinit light zsh-users/zsh-autosuggestions
    # 命令提示
    zinit light shengyou/codeception-zsh-plugin
    # highlight内容
    zinit light zsh-users/zsh-syntax-highlighting
    # 简短(别名)操作提示
    zinit light djui/alias-tips
    # zsh历史搜索
    zinit light zsh-users/zsh-history-substring-search
    # touchbar
    zinit light iam4x/zsh-iterm-touchbar
    # k(ls替代工具)
    zinit light supercrabtree/k
    # 目录跳转(类似z命令)
    zinit light wfxr/formarks
    # Fzf
    zinit light junegunn/fzf
    # fzf的操作工具
    zinit light amaya382/zsh-fzf-widgets
    # fzf版目录跳转
    zinit light urbainvaes/fzf-marks
    # fzf自动补全
    zinit light Aloxaf/fzf-tab
    # yeoman(nodejs的web app)框架的插件
    # zinit light edouard-lopez/yeoman-zsh-plugin
    # 各种git相关命令
    zinit light yh392261226/git-extra-commands
    # dotfile管理工具
    zinit light kazhala/dotbare
    # forgit插件
    zinit light wfxr/forgit
    # git-open插件
    zinit light paulirish/git-open
    # fzf brew插件
    zinit light thirteen37/fzf-brew

    # ASDF
    if [ -d "$HOME/.asdf" ]; then
        zinit ice wait lucid
        # asdf工具
        zinit light asdf-vm/asdf
    else
        mkdir $HOME/.asdf
    fi

    function reload_zinit() {
        source $MYRUNTIME/customs/my_shell/zsh/zmy_zinit.zsh
    }
    alias reloadz="reload_zinit"


    zinit ice lucid wait='2'
    # svn工具
    zinit ice svn
    if [ "starship" = "$(cat $HOME/.prompt_config)" ]; then
        # starship
        eval "$(starship init zsh)"
    elif [ "roundy" = "$(cat $HOME/.prompt_config)" ]; then
        # zsh圆型prompt
        zinit light metaory/zsh-roundy-prompt
### Zsh Roundy Prompt Configures #https://github.com/metaory/zsh-roundy-prompt
ROUNDY_EXITSTATUS_OK="➤"
ROUNDY_EXITSTATUS_NO="➤"
#ROUNDY_TEXC_ICON="✎"
ROUNDY_TEXC_ICON="ﮫ"
ROUNDY_TEXC_MIN_MS=5
ROUNDY_USER_CONTENT_NORMAL=" %n "
ROUNDY_USER_CONTENT_ROOT=" %n "
ROUNDY_DIR_MODE="short"
ROUNDY_PROMPT_HAS_GAP=true

# Command Exit Status
ROUNDY_COLORS_BG_EXITSTATUS_OK=4
ROUNDY_COLORS_FG_EXITSTATUS_OK=0

ROUNDY_COLORS_BG_EXITSTATUS_NO=1
ROUNDY_COLORS_FG_EXITSTATUS_NO=0

# Time Execution of Command
ROUNDY_COLORS_BG_TEXC=2
ROUNDY_COLORS_FG_TEXC=0

# User Display
ROUNDY_COLORS_BG_USER=8
ROUNDY_COLORS_FG_USER=255

# Directory Info
ROUNDY_COLORS_BG_DIR=8
ROUNDY_COLORS_FG_DIR=255

# Git Info
ROUNDY_COLORS_BG_GITINFO=5
ROUNDY_COLORS_FG_GITINFO=0
    else
        zinit ice depth=1
        zinit light romkatv/powerlevel10k
        [[ -f $HOME/.p10k.zsh ]] && source $HOME/.p10k.zsh
    fi
fi

#bindkey ',' autosuggest-accept
