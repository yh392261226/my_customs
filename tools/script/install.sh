#!/bin/bash
##Desc:安装脚本
##Author:杨浩
RUNTIMEPATH="$HOME/data/data/.runtime"

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
brew install lolcat figlet cowsay fortune screenfetch
brew install php@5.6 php@7.0 php@7.1 
brew install antigen rbenv
brew install ctags git astyle tmux node chruby fish lua luajit ag ack tig ranger ruby archey
brew install ghc cabal-install stack terminal-notifier faac
brew install ffmpeg --with-chromaprint --with-fdk-aac --with-fontconfig --with-freetype --with-frei0r --with-game-music-emu --with-libass --with-libbluray --with-libbs2b --with-libcaca --with-libgsm --with-libmodplug --with-librsvg --with-libsoxr --with-libssh --with-libvidstab --with-libvorbis --with-libvpx --with-opencore-amr --with-openh264 --with-openjpeg --with-openssl --with-opus --with-rtmpdump --with-rubberband --with-sdl2 --with-snappy --with-speex --with-tesseract --with-theora --with-tools --with-two-lame --with-wavpack --with-webp --with-x265 --with-xz --with-zeromq --with-zimg
brew install pyenv shellcheck gawk httpie archey 

sudo easy_install -ZU autopep8 twisted
sudo npm install -g jshint jslint csslint jsonlint coffeelint
sudo pip install pyflakes pylint howdoi unittest2 mock compass argparse argcomplete virtualenv virtualenvwrapper dbgp vim-debug pep8 flake8
sudo npm install -g jshint coffee-script jsonlint stylus less serve yalr
sudo gem install vimdeck
sudo npm install -g npmlv npm-mkrelease grunt
sudo gem install sass
sudo gem install json_pure
#install icdiff
pip install git+https://github.com/jeffkaufman/icdiff.git
pip install pexpect pypinyin toml
#install toys
npm install --global pokemon-terminal

#install softwares
brew cask install firefox chrome dropbox java vim neovim anaconda docker
brew install macvim --with-lua

#install oh-my-zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
git clone https://github.com/bhilburn/powerlevel9k.git $HOME/.oh-my-zsh/custom/themes/powerlevel9k
echo 'source $RUNTIMEPATH/customs/my_shell/rcfile' >> $HOME/.zhsrc
ln -sf $HOME/.oh-my-zsh $RUNTIMEPATH/oh-my-zsh
if [ -z fc-cache ]; then
  wget https://github.com/powerline/powerline/raw/develop/font/PowerlineSymbols.otf
  wget https://github.com/powerline/powerline/raw/develop/font/10-powerline-symbols.conf
  mv PowerlineSymbols.otf $HOME/.local/share/fonts/
  fc-cache -vf $HOME/.local/share/fonts/
  mkdir -p $HOME/.config/fontconfig/conf.d/
  mv 10-powerline-symbols.conf $HOME/.config/fontconfig/conf.d/
fi

[[ -d $HOME/.oh-my-zsh ]] && git clone https://github.com/zsh-users/antigen $HOME/.oh-my-zsh/antigen

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
[[ ! -d /tools/ssh-auto-login/auto_gen ]] && mkdir /tools/ssh-auto-login/auto_gen && cp $RUNTIMEPATH/customs/tools/script/config_templates/localhost /tools/ssh-auto-login/auto_gen/
ln -sf $RUNTIMEPATH/customs/bin/getHosts /usr/local/sbin/gethosts
[[ ! -f $RUNTIMEPATH/tools/current_picture ]] && touch $RUNTIMEPATH/tools/current_picture
[[ ! -f $RUNTIMEPATH/tools/current_picturename ]] && touch $RUNTIMEPATH/tools/current_picturename
[[ ! -f $RUNTIMEPATH/tools/fpmark ]] && touch $RUNTIMEPATH/tools/fpmark
[[ ! -f $RUNTIMEPATH/tools/m_bsh ]] && touch $RUNTIMEPATH/tools/m_bsh
[[ ! -d $RUNTIMEPATH/tools/m_date_caches ]] && mkdir $RUNTIMEPATH/tools/m_date_caches
[[ ! -d $RUNTIMEPATH/tools/templates ]] && mkdir $RUNTIMEPATH/tools/templates
[[ ! -f $RUNTIMEPATH/tools/m_dot ]] && touch $RUNTIMEPATH/tools/m_dot
[[ ! -f $RUNTIMEPATH/tools/m_favorate ]] && touch $RUNTIMEPATH/tools/m_favorate
[[ ! -f $RUNTIMEPATH/tools/m_fsh ]] && touch $RUNTIMEPATH/tools/m_fsh
[[ ! -f $RUNTIMEPATH/tools/m_mark ]] && touch $RUNTIMEPATH/tools/m_mark
[[ ! -f $RUNTIMEPATH/tools/m_messagetime ]] && touch $RUNTIMEPATH/tools/m_messagetime
[[ ! -f $RUNTIMEPATH/tools/m_note_mark ]] && touch $RUNTIMEPATH/tools/m_note_mark
[[ ! -f $RUNTIMEPATH/tools/m_nvim ]] && touch $RUNTIMEPATH/tools/m_nvim
[[ ! -f $RUNTIMEPATH/tools/m_scheme ]] && touch $RUNTIMEPATH/tools/m_scheme
[[ ! -f $RUNTIMEPATH/tools/m_scheme_favo ]] && touch $RUNTIMEPATH/tools/m_scheme_favo
[[ ! -f $RUNTIMEPATH/tools/m_sudopass ]] && touch $RUNTIMEPATH/tools/m_sudopass
[[ ! -f $RUNTIMEPATH/tools/m_tmux ]] && touch $RUNTIMEPATH/tools/m_tmux
[[ ! -f $RUNTIMEPATH/tools/m_vim ]] && touch $RUNTIMEPATH/tools/m_vim
[[ ! -f $RUNTIMEPATH/tools/m_zsh ]] && touch $RUNTIMEPATH/tools/m_zsh
[[ ! -f $RUNTIMEPATH/tools/myruntime ]] && touch $RUNTIMEPATH/tools/myruntime
[[ ! -f $RUNTIMEPATH/tools/packagemark ]] && touch $RUNTIMEPATH/tools/packagemark
[[ ! -f $RUNTIMEPATH/tools/positmark ]] && touch $RUNTIMEPATH/tools/positmark
[[ ! -f $RUNTIMEPATH/tools/m_title ]] && cp $RUNTIMEPATH/customs/tools/script/config_templates/m_title $RUNTIMEPATH/tools/m_title
[[ ! -f $RUNTIMEPATH/tools/m_message ]] && cp $RUNTIMEPATH/customs/tools/script/config_templates/m_message $RUNTIMEPATH/tools/m_message
[[ ! -f $RUNTIMEPATH/tools/m_mysql ]] && cp $RUNTIMEPATH/customs/tools/script/config_templates/m_mysql $RUNTIMEPATH/tools/m_mysql
[[ ! -f $RUNTIMEPATH/tools/m_redis ]] && cp $RUNTIMEPATH/customs/tools/script/config_templates/m_redis $RUNTIMEPATH/tools/m_redis
[[ ! -f $RUNTIMEPATH/tools/m_memcached ]] && cp $RUNTIMEPATH/customs/tools/script/config_templates/m_memcached $RUNTIMEPATH/tools/m_memcached
[[ ! -f $RUNTIMEPATH/tools/m_switch_localpic ]] && cp $RUNTIMEPATH/customs/tools/script/config_templates/m_switch_localpic $RUNTIMEPATH/tools/m_switch_localpic
[[ ! -f $RUNTIMEPATH/tools/m_proxy ]] && cp $RUNTIMEPATH/customs/tools/script/config_templates/m_proxy $RUNTIMEPATH/tools/m_proxy
[[ ! -f $RUNTIMEPATH/tools/pictures.php ]] && touch $RUNTIMEPATH/tools/pictures.php

#link softwares
[[ ! -d $HOME/bin ]] && mkdir $HOME/bin
[[ -f /Applications/Visual\ Studio Code.app/Contents/Resources/app/bin/code ]] && ln -sf /Applications/Visual\ Studio Code.app/Contents/Resources/app/bin/code $HOME/bin/code
[[ -f /Applications/Sublime\ Text.app/Contents/SharedSupport/bin/subl ]] && ln -sf /Applications/Sublime\ Text.app/Contents/SharedSupport/bin/subl $HOME/bin/subl
ln -sf $HOME/bin/subl $HOME/bin/st
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --set show_channel_urls yes

#spacevim
[[ ! -d $HOME/.SpaceVim.d ]] && mkdir $HOME/.SpaceVim.d
[[ ! -f $HOME/.SpaceVim.d/init.vim ]] && cp $RUNTIMEPATH/customs/tools/script/config_templates/init.vim $HOME/.SpaceVim.d/init.vim
[[ -f $HOME/.SpaceVim.d/init.toml ]] && mv $HOME/.SpaceVim.d/init.toml $HOME/.SpaceVim.d/bak_init.toml_bak
curl -sLf https://spacevim.org/install.sh | bash

[[ ! -d $HOME/go-develop ]] && mkdir $HOME/go-develop
[[ -d $HOME/bin ]] && wget git.io/trans -O $HOME/bin/trans && chmod +x $HOME/bin/trans

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
