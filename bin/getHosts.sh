#!/bin/bash
today=$(date +%Y%m%d)
markline=34
tmppath=/Users/json/Desktop

##下载下来
#wget https://raw.githubusercontent.com/racaljk/hosts/master/hosts -qO /tmp/${today}.hosts > /dev/null
#wget https://coding.net/u/scaffrey/p/hosts/git/raw/master/hosts -qO /tmp/${today}.hosts > /dev/null
wget https://coding.net/u/scaffrey/p/hosts/git/raw/master/hosts -qO /tmp/${today}.hosts > /dev/null
##把系统原有的备份一个
cat /etc/hosts > /tmp/${today}.hosts.bak
##分割手动的一些hosts
split -l $markline /tmp/${today}.hosts.bak /tmp/tmp_hosts_
##打给临时文件
cat /tmp/tmp_hosts_aa /tmp/${today}.hosts > /tmp/final_${today}.hosts
##删除桌面原有的
rm -f /Users/json/Desktop/hosts
##迁移到桌面去
mv /tmp/final_${today}.hosts $tmppath/hosts
##给windows也覆盖一份
cp $tmppath/hosts /Volumes/BOOTCAMP/Windows/System32/drivers/etc/hosts
##覆盖本系统的hosts
sudo cp $tmppath/hosts /etc/hosts
##删除临时文件与备份
rm -f /tmp/tmp_hosts_* /tmp/${today}.hosts.bak /tmp/${today}.hosts $tmppath/hosts
