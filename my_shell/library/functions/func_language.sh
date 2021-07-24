function fzf_rb() { # Desc: fzf_rb:RVM integration
    local rb
    rb=$(
    (echo system; rvm list | grep ruby | cut -c 4-) |
    awk '{print $1}' |
    fzf-tmux -l 30 +m --reverse) && rvm use $rb
}

function frb() { # Desc: frb:RVM integration
    fzf_rb
}

function gems() { # Desc: gems:rvm多个版本的gem操作同一个包
    for v in 2.0.0 1.8.7 jruby 1.9.3; do
        rvm use $v
        gem $@
    done
}

function rakes() { # Desc: rakes:rvm多个版本的rake操作同一个包
    for v in 2.0.0 1.8.7 jruby 1.9.3; do
        rvm use $v
        rake $@
    done
}



#   mans:   Search manpage given in agument '1' for term given in argument '2' (case insensitive)
#           displays paginated result with colored search terms and two lines surrounding each hit.             Example: mans mplayer codec
#   --------------------------------------------------------------------

function mans () { # Desc: mans:man command[$1] and highlight keyword[$2]
    man $1 | grep -iC2 --color=always $2 | less
}

function memo() { # Desc: memo:依托于cheat.sh的备忘录
    if [ $# -lt 1 ]; then
        echo "Usage:$0 language function"
        echo ""
        echo "---------------------------------------"
        echo ""
        curl cht.sh
        return 0
    fi


    url="cheat.sh/"
    if [ "$1" != "" ]; then
        url="cheat.sh/$1/"
    fi

    if [ "$2" != "" ]; then
        url="cheat.sh/$1/$2"
    fi

    if [ "$3" != "" ]; then
        url="cheat.sh/$1/$2+$3"
    fi
    curl $url
}

function phpcv() { # Desc: phpcv:PHP 依赖于brew 切换已安装版本
    installedPhpVersions=($(brew ls --versions | ggrep -E 'php(@.*)?\s' | ggrep -oP '(?<=\s)\d\.\d' | uniq | sort))
    posit=1
    versions[1]='';
    commands[1]='';
    for phpVersion in ${installedPhpVersions[*]}; do
        value="{"

        for otherPhpVersion in ${installedPhpVersions[*]}; do
            if [ "${otherPhpVersion}" != "${phpVersion}" ]; then
                value="${value} brew unlink php@${otherPhpVersion};"
            fi
        done

        value="${value} brew link php@${phpVersion} --force --overwrite; }  &> /dev/null && php -v"
        versions[$posit]="php_${phpVersion}"
        commands[$posit]=${value}
        echo "$posit : php_${phpVersion}"
        ((posit+=1))
    done

    echo "*******************************************************"
    echo "Current version is : $(php -v)"
    echo "*******************************************************"
    echo "Which version do you want or exit type N/no :"
    read choose
    if [ "$choose" = "N" ] || [ "$choose" = "no" ] || [ "$choose" = "n" ] || [ "$choose" = "NO" ] || [ "$choose" = "No" ]; then
        return 0
    fi
    if [ "$choose" -lt "${#versions[@]}" ]; then
        tmpfile=$(mktemp)
        echo "${commands[$choose]}" > $tmpfile
        bash $tmpfile
        trap 'rm -f "$tmpfile"'
        echo "Now, it's done ..."
    fi
}
