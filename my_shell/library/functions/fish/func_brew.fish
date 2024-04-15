function brew_clean_caches
    # Desc: function: brew_clean_caches:Brew Delete (one or multiple) Caches files of  mnemonic (e.g. uninstall)
    set -l current_dir (pwd)
    cd (brew --cache)
    find . -maxdepth 1 -type f -exec rm -f {} +
    cd (brew --cache)/downloads
    find . -maxdepth 1 -type f -exec rm -f {} +
    echo "Common files already deleted, You have to clean other files manually!!!"
    cd $current_dir
end
alias bcc="brew_clean_caches"

function fzf_brew_delete_by_select
    # Desc: function: fzf_brew_delete_by_select:Brew Delete (one or multiple) selected application(s) mnemonic (e.g. uninstall)
    set uninst (brew leaves | fzf -m $FZF_CUSTOM_PARAMS --preview='brew info {1} | bat --color=always --language=Markdown --style=plain' --header="$(_buildFzfHeader '' 'fzf_brew_delete_by_select')")

    if not test "$uninst" = ""
        for prog in (echo $uninst)
            brew uninstall $prog
        end
    end
end
alias fbd="fzf_brew_delete_by_select"

function fzf_brew_update_by_select
    # Desc: function: fzf_brew_update_by_select:Brew Update (one or multiple) selected application(s) mnemonic [B]rew [U]pdate [P]lugin
    set upd (brew leaves | fzf -m $FZF_CUSTOM_PARAMS --preview='brew info {1} | bat --color=always --language=Markdown --style=plain' --header="$(_buildFzfHeader '' 'fzf_brew_update_by_select')")

    if not test "$upd" = ""
        set upd (echo $upd | sed 's/\n/ /g')
        brew upgrade $upd
    end
end
alias fbup="fzf_brew_update_by_select"

function fzf_brew_upgrade_by_select
    # Desc: function: fzf_brew_upgrade_by_select:Brew upgrade (one or multiple)
    set upgrads (brew outdated | fzf -m $FZF_CUSTOM_PARAMS --preview='brew info {1} | bat --color=always --language=Markdown --style=plain' --header="$(_buildFzfHeader '' 'fzf_brew_upgrade_by_select')")
    if not test "$upgrads" = ""
        set upgrades (echo $upgrads | sed 's/\n/ /g')
        brew upgrade $upgrades
    end
end
alias fbug="fzf_brew_upgrade_by_select"

function reinstall_neovim
    # Desc: function: reinstall_neovim:重新安装neovim
    brew reinstall neovim --HEAD
end
alias renvim="reinstall_neovim"

function fzf_brew_install_by_select
    # Desc: function: fzf_brew_install_by_select:Brew Install (one or multiple) selected application(s) using "brew search" as source input mnemonic [B]rew [I]nstall [P]lugin
    set inst (brew search | fzf -m $FZF_CUSTOM_PARAMS \
        --preview='brew info {1} | bat --color=always --language=Markdown --style=plain' \
        --header=(_buildFzfHeader '' 'fzf_brew_install_by_select'))

    if not test "$inst" = ""
        for prog in (echo $inst)
            brew install $prog
        end
    end
end
alias fbis="fzf_brew_install_by_select"

function fzf_brew_install_or_remove
  set -l wait_click "echo \n\e[34mPress any key to continue...; and read -rsk 1"
  set -l jq_all '(. | map(.cask_tokens) | flatten | map(split("/")[-1] + " (cask)"))[], (. | map(.formula_names) | flatten)[]'
  set -l jq_installed '(.formulae[] | .name), (.casks[] | .token + " (cask)")'
  set -l tmp_file (mktemp)
  trap "rm -f $tmp_file" EXIT
  set -l reload "reload%switch (cat $tmp_file)
    case install
      echo Install mode; brew tap-info --json --installed | jq --raw-output '$jq_all' | sort
    case '*'
      echo Remove mode; brew info --json=v2 --installed | jq --raw-output '$jq_installed' | sort
  end"
  set -l state "cat $tmp_file"
  set -l nextstate "execute-silent%switch (cat $tmp_file)
    case install
      echo rm > $tmp_file
    case '*'
      echo install > $tmp_file
  end"
  set -l bold "\e[1m"
  set -l reset "\e[0m"
  set -l italic "\e[3m"
  set -l gray "\e[30m"
  set -l c "\e[1;36m"
  set -l d "\e[1;37m"
  set -l help "{$bold}{$c}[{$d}B{$c}]rew {$c}[{$d}I{$c}]nteractive{$reset}
  {$italic}Tab{$reset}     Switch between install mode and remove mode
  {$italic}Enter{$reset}   Select formula or cask for installation or deletion (depends on mode)
  {$italic}ctrl-c{$reset}  Show formula or cask installation [s]ource code
  {$italic}ctrl-j{$reset}  Show formula or cask [J]SON information
  {$italic}crtl-e{$reset}  [E]dit formula or cask source code
  {$italic}crtl-y{$reset}  Copy application
  {$italic}crtl-s{$reset}  Switch between sort or no-sort mode
  {$italic}crtl-/{$reset}  Switch between show or hide preview window
  {$italic}?{$reset}       Help (this page)
  {$italic}ESC{$reset}     Quit
  It is also advised you use auto-updates, this can be done with:
      brew autoupdate start --upgrade --cleanup --enable-notification
  "
  echo install > $tmp_file
  echo "Install mode (? for help); brew tap-info --json --installed | jq --raw-output '$jq_all' | sort" | begin
    fzf $FZF_CUSTOM_PARAMS \
        --preview-window right:70%:rounded:hidden:wrap \
        --bind="enter:execute( \
        if test '{2}' = 'cask'
          brew ($state) --cask {1}
        else
          brew ($state) {1}
        end
        $wait_click
        $reload)" \
        --bind='ctrl-c:preview \
        bat --color=always (brew edit --print-path {1}) --style=header' \
        --bind="ctrl-j:preview:brew info --json=v2 {1} | jq '
        (.formulae + .casks)[0] | with_entries(select(try (.value | length > 0)))
      ' | bat --plain --language=json --color=always" \
        --bind="ctrl-e:execute \
        EDITOR='code --wait' brew edit {1}
        bat --color=always --language=markdown --plain <<-MD
          To install the formulae (or cask) you edited with your changes, use:
              brew reinstall --build-from-source {1}
        MD
        $wait_click" \
        --bind="tab:$nextstate+$reload" \
        --bind="?:preview \
        printf '$help'" \
        --preview='brew info {1} | bat --color=always --language=Markdown --style=plain' \
        --header="$(_buildFzfHeader '' 'fzf_brew_install_or_remove')"
  end
end
alias fbm="fzf_brew_install_or_remove"
