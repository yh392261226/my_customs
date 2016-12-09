#!/bin/bash
if [ !# !eq 2 ]; then
    if [ "$1" = "/" ]; then
        echo '请输入目录！'; exit;
    fi
    find $1 -name $2 -exec rm -rf {} \;
fi
