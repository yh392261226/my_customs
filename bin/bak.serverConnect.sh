#!/usr/bin/expect
set addr [lindex $argv 0]
set dir  [lindex $argv 1]
if { $addr=="" } {
    puts "connectserver test|home|working|fenghuang|alienware";
    exit;
}
if { "$addr"=="home" } {
	set address [lindex 192.168.1.18]
	set port [lindex 22]
	set user [lindex root]
	set pwd [lindex yanghao]
	set act [lindex {cd /www/}]
} elseif { "$addr"=="working" } {
    set address [lindex 192.168.30.18]
    set port [lindex 22]
    set user [lindex root]
    set pwd [lindex yanghao]
    set act [lindex {cd /www}]
} elseif { "$addr"=="fenghuang" } {
	set address [lindex 192.168.1.88]
	set port [lindex 22]
	set user [lindex root]
	set pwd [lindex yanghao]
	set act [lindex {cd /www}]
} elseif { "$addr"=="jx" } {
	set address [lindex 192.168.1.10]
	set port [lindex 22]
	set user [lindex root]
	set pwd [lindex 12345qwert]
	set act [lindex {cd /www}]
} elseif { "$addr"=="alienware" } {
	set address [lindex 192.168.1.36]
	set port [lindex 22]
	set user [lindex root]
	set pwd [lindex yanghao1017]
	set act [lindex {cd /data/app/www}]
} elseif { "$addr"=="v" } {
    set address [lindex 72.13.83.202]
    set port [lindex 22]
    set user [lindex root]
    set pwd [lindex bf37d82cdc57afa0d42d24cbcebcacdf8fca6280]
    set act [lindex {cd /home/web/v.sincaitest.com/auto/}]
} elseif { "$addr"=="doing3" } {
    set address [lindex 121.54.174.103]
    set port [lindex 22]
    set user [lindex root]
    set pwd [lindex tgBhu.09]
    set act [lindex {cd /data/app/www/}]
#} elseif { "$addr"=="doing2" } {
#    set address [lindex 103.20.221.237]
#    set port [lindex 22]
#    set user [lindex root]
#    set pwd [lindex 1q2w3e4r5t6y]
#    set act [lindex {cd /data/app/www/}]
#} elseif { "$addr"=="doing" } {
#    set address [lindex 174.139.202.7]
#    set port [lindex 22]
#    set user [lindex root]
#    set pwd [lindex FrE3eyed]
#    set act [lindex {cd /}]
} elseif { "$addr"=="test" } {
    set address [lindex 192.168.146.133]
    set port [lindex 22]
    set user [lindex root]
    set pwd [lindex yanghao]
    set act [lindex {cd /}]
} 
#elseif {$addr==211} {
#	set address [lindex 60.28.208.211]
#	set port [lindex 7710]
#	set user [lindex lianjun.yang]
#	set pwd [lindex YangHao1017]
#}
spawn ssh  -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p$port $user@$address
expect -re "password:" {
    send "$pwd\r"
} 
sleep 1;
    send "\r"
    send "$act\r";
interact
