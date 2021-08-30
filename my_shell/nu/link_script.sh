#!/usr/bin/env bash

ln -sf $MYCUSTOMS/my_shell/nu/config.toml ~/Library/Application\ Support/org.nushell.nu/config.toml
ln -sf $MYCUSTOMS/my_shell/nu/keybinds.yml ~/Library/Application\ Support/org.nushell.nu/keybinds.yml


mkdir -p $HOME/.nu && ln -sf $MYCUSTOMS/my_shell/nu/config $HOME/.nu/config
