#!/bin/bash
host=$1
user=$2
password=$3
port=22
host_name=$5
[[ "" != "$4" ]] && port=$4
[[ "" != "$5" ]] && host_name=$5

rows=$(stty size | awk '{print $1}')
columns=$(stty size | awk '{print $2}')

source $MYRUNTIME/customs/my_shell/my_common.sh
file=$HOME"/.ssh/tmp/master-$user@$host:$port"
info "已登录 $host_name"
if [ -e "$file" ]; then
	echo -e "\033[41;36m 重用 $user@$host:$port \033[0m" 
	ssh $user@$host -p $port
else
	cd $MYRUNTIME/customs/bin/ssh-auto-login/files
	./auto_login.exp $host $user $password $save_RSA_key $port $rows $columns
fi
success "已退出 $host_name"
