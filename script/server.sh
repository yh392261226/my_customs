#!/bin/bash
WORKINGFOLDER=$HOME/Dropbox/working/coding #for example this path is mine

echo "Before using this script, You have to put your configs into your folder: $WORKINGFOLDER/conf/"
echo "And your codes has to be found in your folder: $WORKINGFOLDER/wwwroot"
echo "After actions above, You may have to type admin password bleow."

[[ ! -d /data ]] && sudo mkdir /data && sudo chown -R {whoami} /data && sudo chmod -R 777 /data 
mkdir /data/wwwlogs
ln -sf $WORKINGFOLDER/wwwroot /data/wwwroot

brew install php
brew install mysql
brew install nginx

rm -f /usr/local/lib/php/pecl
mkdir /usr/local/lib/php/pecl

rm -fr /usr/local/etc/php && ln -sf $WORKINGFOLDER/conf/php /usr/local/etc/php
rm -fr /usr/local/etc/nginx && ln -sf $WORKINGFOLDER/conf/nginx /usr/local/etc/nginx
rm -f /usr/local/etc/my.cnf && ln -sf $WORKINGFOLDER/conf/my.cnf /usr/local/etc/my.cnf
rm -f /usr/local/etc/redis.conf && ln -sf $WORKINGFOLDER/conf/redis.conf /usr/local/etc/redis.conf
rm -f /usr/local/etc/redis-sentinel.conf && ln -sf $WORKINGFOLDER/conf/redis-sentinel.conf /usr/local/etc/redis-sentinel.conf

pecl install -f mcrypt
pecl install -f imagick
pecl install xdebug
pecl install memcached
pecl install igbinary
pecl install redis
