export PATH="$(brew --prefix homebrew/php/php71)/bin:$(brew --prefix homebrew/php/php71)/sbin:$PATH"
### add php-school
export PATH="$PATH:/Users/json/.php-school/bin"
source $(brew --prefix php-version)/php-version.sh && php-version 7
