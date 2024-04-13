function print_colors
    # Desc: function: print_colors: 打印终端色彩
    for i in (seq 0 255)
        printf "\x1b[38;5;%imcolor%-5i\x1b[0m" $i $i
        if not math $i % 8
            echo
        end
    end
end

abbr -a pcolors print_colors # Desc: alias: pcolors: print_colors命令的别名,打印终端色彩
