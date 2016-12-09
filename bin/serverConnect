#!/usr/bin/expect
#### old auto connect to server by the alias names

set addr [lindex $argv 0]
set dir  [lindex $argv 1]
if { $addr=="" } {
	puts "connectserver centos| locentos| locentos2";
	exit;
}
if { "$addr"=="centos" } {
	set address [lindex 192.168.0.114]
	set port [lindex 22]
	set user [lindex root]
	set pwd [lindex yanghao]
	set act [lindex {cd /data/app/www}]
	set act2 [lindex {  }]
	#	set act [lindex {chown -R nginx:nginx /var/lib/php/session }]
} elseif { "$addr"=="locentos" } {
set address [lindex 10.211.55.5]
set port [lindex 22]
set user [lindex root]
set pwd [lindex yanghao1017]
set act [lindex {}]
set act2 [lindex {}]
 } elseif { "$addr"=="locentos2" } {
 set address [lindex 10.211.55.10]
 set port [lindex 22]
 set user [lindex root]
 set pwd [lindex yanghao1017]
 set act [lindex {}]
 set act2 [lindex {}]
}
spawn ssh  -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p$port $user@$address
expect -re "password:" {
send "$pwd\r"
}
sleep 1
send "\r"
send "$act\r"
sleep 2
send "\r"
send "$act2\r"
interact
