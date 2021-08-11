function brew_clean_caches() { # Desc: brew_clean_caches:Brew Delete (one or multiple) Caches files of  mnemonic (e.g. uninstall)
  customcd $(brew --cache)
  rm -f ./*phar ./*patch ./*diff ./*xz ./*gz ./*bz2 ./*zip ./*rock
  rm -rf ./*git
  customcd $(brew --cache)/downloads
  rm -f ./*phar ./*patch ./*diff ./*xz ./*gz ./*bz2 ./*zip ./*rock
  echo "Common files already deleted, You have to clean other files manually!!!"
}
alias bcc="brew_clean_caches"

function fzf_brew_delete_by_select() { # Desc: fzf_brew_delete_by_select:Brew Delete (one or multiple) selected application(s) mnemonic (e.g. uninstall)
  local uninst=$(brew leaves | fzf -m)

  if [[ $uninst ]]; then
    for prog in $(echo $uninst); do
        brew uninstall $prog; 
    done;
  fi
}
alias fzf_bdl="fzf_brew_delete_by_select"

function fzf_brew_update_by_select() { # Desc: fzf_brew_update_by_select:Brew Update (one or multiple) selected application(s) mnemonic [B]rew [U]pdate [P]lugin
  local upd=$(brew leaves | fzf -m)

  if [[ $upd ]]; then
    for prog in $(echo $upd);do
        brew upgrade $prog;
    done;
  fi
}
alias fzf_bup="fzf_brew_update_by_select"
alias bup="fzf_brew_update_by_select"

function reinstallneovim() { # Desc: reinstallneovim:重新安装neovim
  brew reinstall neovim --HEAD
}

function fzf_brew_install_by_select() { # Desc: fzf_brew_install_by_select:Brew Install (one or multiple) selected application(s) using "brew search" as source input mnemonic [B]rew [I]nstall [P]lugin
  local inst=$(brew search | fzf -m)

  if [[ $inst ]]; then
    for prog in $(echo $inst);do
        brew install $prog;
    done;
  fi
}
alias fzf_bip="fzf_brew_install_by_select"
alias bip="fzf_brew_install_by_select"