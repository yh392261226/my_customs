if [ -n "$TMUX_PANE" ]; then
    # Desc: tmux中 https://github.com/wellle/tmux-complete.vim
    function fzf_tmux_words() {
        fzf_tmux_helper \
            '-p 40' \
            'tmuxwords.rb --all --scroll 500 --min 5 | fzf --multi | paste -sd" " -'
    }
fi