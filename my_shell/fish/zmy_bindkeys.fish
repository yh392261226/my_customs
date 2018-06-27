function changebg_key_bindings
    fish_vi_key_bindings
	bind -M insert \cq bg_rand_pre
	bind -M insert \cw bg_rand
	bind -M insert \ce bg_rand_next
	bind -M insert \cb bg_empty
end
set -g fish_key_bindings changebg_key_bindings
