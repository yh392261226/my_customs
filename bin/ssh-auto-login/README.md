Auto input password for login in, and access a host by a customized alias command.

1.  You may have a acount can access lots of servers:

Use `source install.sh` to install `to` alias command, after installation, you can access a host by:

```bash
# use source to let the alias take effect
$ source install.sh username password
$ to 192.168.154.101
```

2.  You may access a server frequently:

Use `source install_shortcut.sh` to install alias command for a realated host, after installation, you can access it  by alias command:

```bash
# use source to let the alias take effect
$ source install_shortcut.sh to-101 username@192.168.154.101
$ to-101
```

**Attention:**

> Your account and password infomation will store in `auto_gen` directory.
> Keep that in mind and delete the whole directory after you finish you work.





使用方法：
sh install_shortcut.sh 别名 用户名@ip地址
如果端口不是默认的22   参考shanghai 新增端口变量
https://github.com/liaohuqiu/ssh-auto-login
