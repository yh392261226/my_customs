#!/bin/bash
WORKINGFOLDER=$HOME/Dropbox/working #for example this path is mine

echo "Before using this script, You have to put your configs into your folder: $WORKINGFOLDER/conf/"
echo "And your codes has to be found in your folder: $WORKINGFOLDER/wwwroot"
echo "This script install PHP, Nginx and Mysql by brew command, So make sure you have got brew command already!"
echo "After actions above, You may have to type admin password bleow."

command -v brew >/dev/null 2>&1 || (echo "You do not have brew command ... You should install it first" && exit 1)

[[ ! -d /data ]] && sudo mkdir /data && sudo chown -R {whoami} /data && sudo chmod -R 777 /data 
mkdir /data/wwwlogs
ln -sf $WORKINGFOLDER/coding/wwwroot /data/wwwroot
ln -sf $WORKINGFOLDER/documents /data/documents

brew install php nginx redis memcached imagemagic

rm -f /usr/local/lib/php/pecl
mkdir /usr/local/lib/php/pecl

rm -fr /usr/local/etc/php && ln -sf $WORKINGFOLDER/coding/conf/php /usr/local/etc/php
rm -fr /usr/local/etc/nginx && ln -sf $WORKINGFOLDER/coding/conf/nginx /usr/local/etc/nginx
rm -f /usr/local/etc/my.cnf && ln -sf $WORKINGFOLDER/coding/conf/my.cnf /usr/local/etc/my.cnf
rm -f /usr/local/etc/redis.conf && ln -sf $WORKINGFOLDER/coding/conf/redis.conf /usr/local/etc/redis.conf
rm -f /usr/local/etc/redis-sentinel.conf && ln -sf $WORKINGFOLDER/coding/conf/redis-sentinel.conf /usr/local/etc/redis-sentinel.conf

echo "If display something to choice below, up to you.(why not try Enter to the end...)"
pecl install -f mcrypt
pecl install -f imagick
pecl install xdebug
pecl install memcached
pecl install igbinary
pecl install redis

echo "PHP & Nginx has already install finished, next is Mysql,"
echo  "after install, You have to setting it by yourself..."
brew install mysql
