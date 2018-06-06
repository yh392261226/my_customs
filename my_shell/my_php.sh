#export PATH="$(brew --prefix homebrew/core/php@72)/bin:$(brew --prefix homebrew/core/php@72)/sbin:$PATH"
### add php-school
export PATH="$PATH:/Users/json/.php-school/bin"
source $(brew --prefix php-version)/php-version.sh && php-version 7
