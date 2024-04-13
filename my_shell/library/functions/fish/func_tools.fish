function create_tmp_aliases
    if test (count $argv) -gt 0
        set tmp_command_file (mktemp)
        echo $tmp_command_file
        # 创建临时脚本
        set n 1
        for command in $argv
            echo $command
            echo "alias a$n=\"$command\"\n" >> $tmp_command_file
            set n (math $n + 1)
        end
        if test -f $tmp_command_file
            source $tmp_command_file
        end
    else
        return
    end
end
alias cta create_tmp_aliases
