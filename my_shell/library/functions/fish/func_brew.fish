function brew_clean_caches
  customcd (brew --cache)
  rm -f ./*phar ./*patch ./*diff ./*xz ./*gz ./*bz2 ./*zip ./*rock
  rm -rf ./*git
  customcd (brew --cache)/downloads
  rm -f ./*phar ./*patch ./*diff ./*xz ./*gz ./*bz2 ./*zip ./*rock
  echo "Common files already deleted, You have to clean other files manually!!!"
end

function fzf_brew_delete_by_select
  set uninst (brew leaves | fzf -m)

  if test $uninst = 1
    for prog in (echo $uninst)
        brew uninstall $prog; 
    end
  end
end

function fzf_brew_update_by_select
  set upd (brew leaves | fzf -m)

  if test $upd = 1
    for prog in (echo $upd)
        brew upgrade $prog;
    end
  end
end

function reinstallneovim
  brew reinstall neovim --HEAD
end

function fzf_brew_install_by_select
  set inst (brew search | fzf -m)

  if test $inst = 1
    for prog in (echo $inst)
        brew install $prog;
    end
  end
end
