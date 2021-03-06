function vmi() { # Desc: vmi:安装一个或多个版本的语言包 e.g. `vmi rust` # => fzf multimode, tab to mark, enter to install if no plugin is supplied (e.g. `vmi<CR>`), fzf will list them for you Mnemonic [V]ersion [M]anager [I]nstall
  local lang=${1}

  if [[ ! $lang ]]; then
    lang=$(asdf plugin-list | fzf)
  fi

  if [[ $lang ]]; then
    local versions=$(asdf list-all $lang | fzf -m)
    if [[ $versions ]]; then
      for version in $(echo $versions); do
        asdf install $lang $version;
      done;
    fi
  fi
}

function vmc() { # Desc: vmc:删除一个或多个版本的语言包 e.g. `vmi rust` # => fzf multimode, tab to mark, enter to remove if no plugin is supplied (e.g. `vmi<CR>`), fzf will list them for you Mnemonic [V]ersion [M]anager [C]lean
  local lang=${1}

  if [[ ! $lang ]]; then
    lang=$(asdf plugin-list | fzf)
  fi

  if [[ $lang ]]; then
    local versions=$(asdf list $lang | fzf -m)
    if [[ $versions ]]; then
      for version in $(echo $versions); do
        asdf uninstall $lang $version; 
      done;
    fi
  fi
}