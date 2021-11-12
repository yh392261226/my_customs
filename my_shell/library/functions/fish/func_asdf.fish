function fzf_vmi # Desc: fzf_vmi:安装一个或多个版本的语言包 e.g. `vmi rust` # => fzf multimode, tab to mark, enter to install if no plugin is supplied (e.g. `vmi<CR>`), fzf will list them for you Mnemonic [V]ersion [M]anager [I]nstall
  local lang=${1}

  if test ! $lang
    lang=$(asdf plugin-list | fzf)
  end

  if test $lang
    local versions=$(asdf list-all $lang | fzf -m)
    if test $versions
      for version in $(echo $versions); do
        asdf install $lang $version;
      done;
    end
  end
end
alias vmi="fzf_vmi"

function fzf_vmc() { # Desc: fzf_vmc:删除一个或多个版本的语言包 e.g. `vmi rust` # => fzf multimode, tab to mark, enter to remove if no plugin is supplied (e.g. `vmi<CR>`), fzf will list them for you Mnemonic [V]ersion [M]anager [C]lean
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
alias vmc="fzf_vmc"