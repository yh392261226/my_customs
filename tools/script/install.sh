#!/bin/bash
##Desc:安装脚本
##Author:杨浩
RUNTIMEPATH="$HOME/.runtime"

[[ ! -d $RUNTIMEPATH ]] && git clone git@github.com:yh392261226/my_customs.git $RUNTIMEPATH && $RUNTIMEPATH/script/install.sh
cd $RUNTIMEPATH && git pull

echo "Starting Install, You may type sudo password many times !"
echo '...'
#install brew first
command -v brew >/dev/null 2>&1 || /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

[[ ! -f $HOME/.myruntime ]] && touch $HOME/.myruntime && echo $RUNTIMEPATH > $HOME/.myruntime
ln -sf $HOME/Pictures $RUNTIMEPATH/pictures

#install zshell & fish shell
brew install zsh fish 

#install some depends
brew install aircrack-ng bfg binutils binwalk cifer dex2jar dns2tcp fcrackzip foremost hashpump hydra john knock netpbm nmap pngcheck socat sqlmap tcpflow tcptrace ucspi-tcp xpdf xz ack lua lynx p7zip pigz pv rename rlwrap ssh-copy-id tree vbindiff zopfli bash-completion2 findutils moreutils coreutils wget gnupg grep openssh tmux bash cargo-completion autojump trash mytop htop expect redis memcached libmemcached mcrypt mycli memcache-top sqlite postgresql python@2 bash-git-prompt git fontconfig
brew install php@5.6
brew install antigen rbenv
brew install ctags git astyle tmux node chruby fish lua luajit ag ack tig ranger ruby archey
sudo easy_install -ZU autopep8 twisted
brew install ghc cabal-install stack terminal-notifier
sudo npm install -g jshint jslint csslint jsonlint coffeelint
sudo pip install pyflakes pylint howdoi unittest2 mock compass argparse argcomplete virtualenv virtualenvwrapper dbgp vim-debug
sudo npm install -g jshint coffee-script jsonlint stylus less serve yalr
sudo gem install vimdeck
sudo npm install -g npmlv npm-mkrelease grunt
sudo gem install sass
sudo gem install json_pure

#install softwares
brew cask install firefox chrome dropbox java vim neovim
brew install macvim --with-lua

#install oh-my-zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
git clone https://github.com/bhilburn/powerlevel9k.git $HOME/.oh-my-zsh/custom/themes/powerlevel9k
echo 'source $RUNTIMEPATH/customs/my_shell/rcfile' >> $HOME/.zhsrc
if [ -z fc-cache ]; then
  wget https://github.com/powerline/powerline/raw/develop/font/PowerlineSymbols.otf
  wget https://github.com/powerline/powerline/raw/develop/font/10-powerline-symbols.conf
  mv PowerlineSymbols.otf $HOME/.local/share/fonts/
  fc-cache -vf $HOME/.local/share/fonts/
  mkdir -p $HOME/.config/fontconfig/conf.d/
  mv 10-powerline-symbols.conf $HOME/.config/fontconfig/conf.d/
fi

#install oh-my-fish
curl -L https://get.oh-my.fish | fish
echo 'source $RUNTIMEPATH/customs/my_shell/fish/zmy_basic.fish' >> $HOME/.config/fish/conf.d/omf.fish
echo 'source $RUNTIMEPATH/customs/my_shell/fish/zmy_bindkeys.fish' >> $HOME/.config/fish/conf.d/omf.fish
echo 'source $RUNTIMEPATH/customs/my_shell/fish/zmy_changebg.fish' >> $HOME/.config/fish/conf.d/omf.fish
ln -sf $RUNTIMEPATH/customs/my_shell/fish/zmy_bindkeys.fish $HOME/.config/fish/functions/zmy_bindkeys.fish
#add fish to shells
sudo echo "/usr/local/bin/fish" >> /etc/shells

#install bash-it
git clone --depth=1 https://github.com/Bash-it/bash-it.git $HOME/.bash_it
$HOME/.bash_it/install.sh
if [ ! -f $HOME/.bashrc ]; then
  ln -sf $HOME/.bash_profile $HOME/.bashrc
fi

#create some directories and files
sudo mkdir /tools/
sudo chmod 777 /tools
sudo chown $(whoami) /tools
ln -sf $RUNTIMEPATH/customs/bin/ssh-auto-login /tools/ssh-auto-login
ln -sf $RUNTIMEPATH/customs/bin/getHosts /usr/local/sbin/gethosts
cd $RUNTIMEPATH/tools/ 
[[ ! -f current_picture ]] && touch current_picture
[[ ! -f current_picturename ]] && touch current_picturename
[[ ! -f fpmark ]] && touch fpmark
[[ ! -f m_bsh ]] && touch m_bsh
[[ ! -d m_date_caches ]] && mkdir m_date_caches
[[ ! -d templates ]] && mkdir templates
[[ ! -f m_dot ]] && touch m_dot
[[ ! -f m_favorate ]] && touch m_favorate
[[ ! -f m_fsh ]] && touch m_fsh
[[ ! -f m_mark ]] && touch m_mark
[[ ! -f m_message ]] && touch m_message
[[ ! -f m_messagetime ]] && touch m_messagetime
[[ ! -f m_note_mark ]] && touch m_note_mark
[[ ! -f m_nvim ]] && touch m_nvim
[[ ! -f m_scheme ]] && touch m_scheme
[[ ! -f m_scheme_favo ]] && touch m_scheme_favo
[[ ! -f m_sudopass ]] && touch m_sudopass
[[ ! -f m_title ]] && touch m_title
[[ ! -f m_tmux ]] && touch m_tmux
[[ ! -f m_vim ]] && touch m_vim
[[ ! -f m_zsh ]] && touch m_zsh
[[ ! -f myruntime ]] && touch myruntime
[[ ! -f packagemark ]] && touch packagemark
[[ ! -f positmark ]] && touch positmark
[[ ! -f m_mysql ]] && touch m_mysql
[[ ! -f m_redis ]] && touch m_redis
[[ ! -f m_memcached ]] && touch m_memcached
[[ ! -f pictures.php ]] && touch pictures.php

#link softwares
[[ ! -d $HOME/bin ]] && mkdir $HOME/bin
[[ -f /Applications/Visual\ Studio Code.app/Contents/Resources/app/bin/code ]] && ln -sf /Applications/Visual\ Studio Code.app/Contents/Resources/app/bin/code $HOME/bin/code
[[ -f /Applications/Sublime\ Text.app/Contents/SharedSupport/bin/subl ]] && ln -sf /Applications/Sublime\ Text.app/Contents/SharedSupport/bin/subl $HOME/bin/subl
ln -sf $HOME/bin/subl $HOME/bin/st


#notice
echo "If you want to use fish / zsh instead bash, You can type these:"
echo "chsh -s /bin/zsh or chsh -s /usr/local/bin/fish"
echo "to change your default shell"
echo "----------------------------------------------------------"
echo "Type your sudo password into $RUNTIMEPATH/tools/m_sudopass"
echo "Type your mysql user, password, host, port into $RUNTIMEPATH/tools/m_mysql"
echo "Type your redis host, port into $RUNTIMEPATH/tools/m_redis"
echo "Type your memcached host, port into $RUNTIMEPATH/tools/m_memcached"
echo "Done ..."
