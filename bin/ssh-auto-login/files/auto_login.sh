#!/bin/bash
host=$1
user=$2
password=$3
port=22
if [ "" != "$4" ]; then
	port=$4
fi

rows=$(stty size | awk '{print $1}')
columns=$(stty size | awk '{print $2}')

file=$HOME"/.ssh/master-$user@$host:$port"
if [ -e "$file" ]; then
	ssh $user@$host -p $port
else
	cd $MYRUNTIME/customs/bin/ssh-auto-login/files
	./auto_login.exp $host $user $password $save_RSA_key $port $rows $columns
fi
