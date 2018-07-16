#!/bin/bash
###Desc:代理
[[ -f $MYRUNTIME/tools/m_proxy ]] && source $MYRUNTIME/tools/m_proxy && export http_proxy=http://${ip}:${port};export https_proxy=http://${ip}:${port};
