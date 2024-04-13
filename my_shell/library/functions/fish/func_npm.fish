function __getnpmpkg
    set -a locks "package-lock.json" "yarn.lock" "pnpm-lock.yaml"
    set -a pkgs "npm" "yarn" "pnpm"
    set pkgcmd npm
    set i 0
    for lock in $locks
        set i (math $i + 1)
        if test -f $lock
            set pkgcmd $pkgs[$i]
            break
        end
    end
    echo $pkgcmd
end

function fzf_npm_run
    set pkgcmd (__getnpmpkg)
    if not test -f package.json
        echo "package.json not found" >&2
    else if test -z $argv[1]
        set command (jq -r '.scripts | keys[]' package.json | tr -d '"' | 
        fzf $FZF_CUSTOM_PARAMS \
          --preview-window=:wrap \
          --preview "jq '.scripts.\"{}\"' package.json -r | tr -d '\"' | sed 's/^[[:blank:]]*//'" \
          --header=(_buildFzfHeader '' 'fzf_npm_run'))

        if test -n $command
            eval "$pkgcmd run $command"
        end
    else
        eval "$pkgcmd run $argv"
    end
end
alias fnr fzf_npm_run

function npm_install
    set pkgcmd (__getnpmpkg)
    # 如果 $argv[1] 为空，则是安装全部依赖
    if test -z $argv[1]
        eval "$pkgcmd install"
    else if test $argv[1] = '-D'; and test -z $argv[2]
        eval "$pkgcmd install -D"
    else
        # 如果是 yarn 安装依赖 使用 add
        if test "$pkgcmd" = "yarn"
            eval "$pkgcmd add $argv"
        else
            eval "$pkgcmd install $argv"
        end
    end
end
alias ni npm_install

function fzf_npm_update
    set pkgcmd (__getnpmpkg)
    # 如果 $argv 为空，则使用 fzf 查找依赖
    if test -z $argv
        set command (jq -r '{dependencies, devDependencies} | to_entries[] | .value | keys[]' package.json |
        fzf $FZF_CUSTOM_PARAMS \
          --preview-window=:wrap \
          --header=(_buildFzfHeader '' 'fzf_npm_update') \
          -m)
        if test -n $command
            eval (echo -n "$pkgcmd remove $command")
        end
    else
        eval "$pkgcmd remove $argv"
    end
end
alias fnu fzf_npm_update
