function bcc() { # Desc: bcc:Brew Delete (one or multiple) Caches files of  mnemonic (e.g. uninstall)
  customcd $(brew --cache)
  rm -f ./*phar ./*patch ./*diff ./*xz ./*gz ./*bz2 ./*zip ./*rock
  rm -rf ./*git
  customcd $(brew --cache)/downloads
  rm -f ./*phar ./*patch ./*diff ./*xz ./*gz ./*bz2 ./*zip ./*rock
  echo "Common files already deleted, You have to clean other files manually!!!"
}

function fzf_bdl() { # Desc: fzf_bdl:Brew Delete (one or multiple) selected application(s) mnemonic (e.g. uninstall)
  local uninst=$(brew leaves | fzf -m)

  if [[ $uninst ]]; then
    for prog in $(echo $uninst); do
        brew uninstall $prog; 
    done;
  fi
}

function bdl() { # Desc: bdl:Brew Delete (one or multiple) selected application(s) mnemonic (e.g. uninstall)
  fzf_bdl
}

function fzf_bup() { # Desc: bup:Brew Update (one or multiple) selected application(s) mnemonic [B]rew [U]pdate [P]lugin
  local upd=$(brew leaves | fzf -m)

  if [[ $upd ]]; then
    for prog in $(echo $upd);do
        brew upgrade $prog;
    done;
  fi
}

function bup() { # Desc: bup:Brew Update (one or multiple) selected application(s) mnemonic [B]rew [U]pdate [P]
  fzf_bup
}

function reinstallneovim() { # Desc: reinstallneovim:重新安装neovim
  brew reinstall neovim --HEAD
}

function fzf_bip() { # Desc: fzf_bip:Brew Install (one or multiple) selected application(s) using "brew search" as source input mnemonic [B]rew [I]nstall [P]lugin
  local inst=$(brew search | fzf -m)

  if [[ $inst ]]; then
    for prog in $(echo $inst);do
        brew install $prog;
    done;
  fi
}

function bip() { # Desc: bip:Brew Install (one or multiple) selected application(s) using "brew search" as 
  fzf_bip
}