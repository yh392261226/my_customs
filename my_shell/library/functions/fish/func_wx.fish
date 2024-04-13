function update_wechat_tool
    cd /tmp/; and git clone --depth=1 https://github.com/MustangYM/WeChatExtension-ForMac; and cd WeChatExtension-ForMac/WeChatExtension/Rely; and ./Install.sh
    rm -rf /tmp/WeChatExtension-ForMac/
    cd -
end
alias uwt="update_wechat_tool"
