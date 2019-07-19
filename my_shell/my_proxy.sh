#!/usr/bin/env bash
###Desc:代理
switcher=0
[[ -f $MYRUNTIME/tools/m_proxy ]] && source $MYRUNTIME/tools/m_proxy 
[[ "$switcher" = "1" ]] && export http_proxy=http://${ip}:${port} && export https_proxy=http://${ip}:${port}
