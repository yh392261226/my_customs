#!/bin/bash
##Desc:安装脚本
##Author:杨浩

#install brew first
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

#install zshell & fish shell
brew install zsh fish 

#install some depends
brew install aircrack-ng bfg binutils binwalk cifer dex2jar dns2tcp fcrackzip foremost hashpump hydra john knock netpbm nmap pngcheck socat sqlmap tcpflow tcptrace ucspi-tcp xpdf xz ack git-lsf lua lynx p7zip pigz pv rename rlwrap ssh-copy-id tree vbindiff zopfli bash-completion2 findutils moreutils coreutils wget gnupg grep openssh tmux bash cargo-completion autojump trash mytop htop expect redis memcached libmemcached mcrypt mycli memcache-top sqlite postgresql python@2 bash-git-prompt git fontconfig
brew install php@5.6
brew install antigen rbenv

#install softwares
brew cask install firefox chrome dropbox java vim neovim
brew install macvim --with-lua

#install oh-my-zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
git clone https://github.com/bhilburn/powerlevel9k.git ~/.oh-my-zsh/custom/themes/powerlevel9k
echo 'source $HOME/.runtime/customs/my_shell/rcfile' >> ~/.zhsrc
if [ -z fc-cache ]; then
  wget https://github.com/powerline/powerline/raw/develop/font/PowerlineSymbols.otf
  wget https://github.com/powerline/powerline/raw/develop/font/10-powerline-symbols.conf
  mv PowerlineSymbols.otf ~/.local/share/fonts/
  fc-cache -vf ~/.local/share/fonts/
  mkdir -p ~/.config/fontconfig/conf.d/
  mv 10-powerline-symbols.conf ~/.config/fontconfig/conf.d/
fi

#install oh-my-fish
curl -L https://get.oh-my.fish | fish
echo 'source $HOME/.runtime/customs/my_shell/fish/zmy_basic.fish' >> ~/.config/fish/conf.d/omf.fish
echo 'source $HOME/.runtime/customs/my_shell/fish/zmy_bindkeys.fish' >> ~/.config/fish/conf.d/omf.fish
echo 'source $HOME/.runtime/customs/my_shell/fish/zmy_changebg.fish' >> ~/.config/fish/conf.d/omf.fish
ln -sf ~/.runtime/customs/my_shell/fish/zmy_bindkeys.fish ~/.config/fish/functions/zmy_bindkeys.fish
#add fish to shells
sudo echo "/usr/local/bin/fish" >> /etc/shells

#install bash-it
git clone --depth=1 https://github.com/Bash-it/bash-it.git ~/.bash_it
~/.bash_it/install.sh
if [ ! -f $HOME/.bashrc ]; then
  ln -sf $HOME/.bash_profile $HOME/.bashrc
fi

#create some directories and files
sudo mkdir /tools/
sudo chmod 777 /tools
sudo chown $(whoami) /tools
ln -sf $HOME/.runtime/customs/bin/ssh-auto-login /tools/ssh-auto-login
cd ~/.runtime/tools/ 
touch current_picture
touch current_picturename
touch fpmark
touch m_bsh
mkdir m_data_caches
mkdir m_date_caches
mkdir templates
touch m_dot
touch m_favorate
touch m_fsh
touch m_mark
touch m_message
touch m_messagetime
touch m_note_mark
touch m_nvim
touch m_scheme
touch m_scheme_favo
touch m_sudopass
touch m_title
touch m_tmux
touch m_vim
touch m_zsh
touch myruntime
touch packagemark
touch positmark
touch m_mysql
touch m_redis
touch m_memcached
touch pictures.php

#install web server
brew install nginx mysql


#notice
echo "If you want to use fish / zsh instead bash, You can type these:"
echo "chsh -s /bin/zsh or chsh -s /usr/local/bin/fish"
echo "to change your default shell"
echo "----------------------------------------------------------"
echo "Don't forget to change your pictures location in ~/.runtime/customs/other/pictures.php"
echo "Type your sudo password into ~/.runtime/tools/m_sudopass"
echo "Type your mysql user, password, host, port into ~/.runtime/tools/m_mysql"
echo "Type your redis host, port into ~/.runtime/tools/m_redis"
echo "Type your memcached host, port into ~/.runtime/tools/m_memcached"
echo "Done ..."