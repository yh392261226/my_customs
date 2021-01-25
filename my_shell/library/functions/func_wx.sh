function update_wx_tool() { # Desc: 更新微信小助手
    cd /tmp/ && git clone --depth=1 https://github.com/MustangYM/WeChatExtension-ForMac && cd WeChatExtension-ForMac/WeChatExtension/Rely && ./Install.sh
    rm -rf /tmp/WeChatExtension-ForMac/
}