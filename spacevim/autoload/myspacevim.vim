function! myspacevim#before() abort
    let g:loaded_python_provider = 1
    let g:python2_host_prog = '/usr/bin/python2'
    let g:python3_host_prog = '/usr/bin/python3'
"    set pyxversion = 3

    "key mapping
    inoremap jj <esc>
    set clipboard+=unnamedplus
    "逗号后空格
    inoremap , ,<Space>
    "等号左右空格
    inoremap = <Space>=<Space>
    nmap <silent> <A-k> :wincmd k<CR>
    nmap <silent> <A-j> :wincmd j<CR>
    nmap <silent> <A-h> :wincmd h<CR>
    nmap <silent> <A-l> :wincmd l<CR>

    " SimpylFold
    let g:SimpylFold_docstring_preview = 1

    "ale
    let g:ale_linters = {
    \   'python': ['pyls'],
    \}
    let g:ale_fixers = {
    \   'python': ['yapf'],
    \   'r': ['trim_whitespace', 'remove_trailing_lines'],
    \}
    let g:ale_sign_column_always = 1
    "let g:ale_r_lintr_options = 'lintr::with_defaults(line_length_linter = lintr::line_length_linter(100))'
    let g:ale_echo_msg_error_str = 'E'
    let g:ale_echo_msg_warning_str = 'W'
    let g:ale_echo_msg_format = '[%linter%] %s [%severity%]'
    nmap <F9> <Plug>(ale_fix)

    "Nvim-R config
"    if $DISPLAY != ""
"        let R_openpdf = 1
"    endif
"    let r_syntax_folding = 1
"    let rrst_syn_hl_chunk = 1
"    let rmd_syn_hl_chunk = 1
"    "let R_objbr_place = 'console,top'
"    let R_objbr_h = 15
"    let R_hi_fun_paren = 1
"    let Rout_more_colors = 1
"    au TermOpen * setlocal nonu

    "indentguides
    let g:indentguides_firstlevel = 1
    let g:indentguides_ignorelist = ['text', 'rmd', 'markdown', 'tex', 'rmarkdown', 'pandoc', 'nerdtree']

    let g:indentguides_spacechar = '¦'
    let g:indentguides_tabchar = '¦'
    " let g:indentguides_conceal_color = 'ctermfg=238 ctermbg=234 guifg=#4e4e4e guibg=NONE'

    "pandoc
    let g:pandoc#folding#fold_yaml = 1

    "ultisnips
    let g:snips_author = "Hao Yang"
    let g:snips_email = "yh392261226@gmail.com"
    let g:snips_github = "https://github.com/yh392261226"

    " automately add the file head for alpertuna/vim-header
    let g:header_auto_add_header = 0
    let g:header_field_modified_timestamp = 0
    let g:header_field_author = 'Hao Yang'
    let g:header_field_author_email = 'yh392261226@gmail.com'
    let g:header_field_timestamp_format = '%Y-%m-%d'

    " junegunn/goyo.vim
    "let g:goyo_width = 100
    "let g:goyo_height = 90%
    "let g:goyo_linenr = 0

    " junegunn/limelight.vim
    " Color name (:help cterm-colors) or ANSI code
    let g:limelight_conceal_ctermfg = 'gray'
    let g:limelight_conceal_ctermfg = 240

    " Color name (:help gui-colors) or RGB color
    let g:limelight_conceal_guifg = 'DarkGray'
    let g:limelight_conceal_guifg = '#777777'

    " Default: 0.5
    let g:limelight_default_coefficient = 0.7

    " Number of preceding/following paragraphs to include (default: 0)
    let g:limelight_paragraph_span = 1

    " Beginning/end of paragraph
    "   When there's no empty line between the paragraphs
    "   and each paragraph starts with indentation
    let g:limelight_bop = '^\s'
    let g:limelight_eop = '\ze\n^\s'

    " Highlighting priority (default: 10)
    "   Set it to -1 not to overrule hlsearch
    let g:limelight_priority = -1

    "voldikss/vim-floaterm
    let g:floaterm_keymap_toggle = '<F12>'


    let g:user_emmet_settings = {
  \ 'wxss': {
  \   'extends': 'css',
  \ },
  \ 'wxml': {
  \   'extends': 'html',
  \   'aliases': {
  \     'div': 'view',
  \     'span': 'text',
  \   },
  \  'default_attributes': {
  \     'block': [{'wx:for-items': '{{list}}','wx:for-item': '{{item}}'}],
  \     'navigator': [{'url': '', 'redirect': 'false'}],
  \     'scroll-view': [{'bindscroll': ''}],
  \     'swiper': [{'autoplay': 'false', 'current': '0'}],
  \     'icon': [{'type': 'success', 'size': '23'}],
  \     'progress': [{'precent': '0'}],
  \     'button': [{'size': 'default'}],
  \     'checkbox-group': [{'bindchange': ''}],
  \     'checkbox': [{'value': '', 'checked': ''}],
  \     'form': [{'bindsubmit': ''}],
  \     'input': [{'type': 'text'}],
  \     'label': [{'for': ''}],
  \     'picker': [{'bindchange': ''}],
  \     'radio-group': [{'bindchange': ''}],
  \     'radio': [{'checked': ''}],
  \     'switch': [{'checked': ''}],
  \     'slider': [{'value': ''}],
  \     'action-sheet': [{'bindchange': ''}],
  \     'modal': [{'title': ''}],
  \     'loading': [{'bindchange': ''}],
  \     'toast': [{'duration': '1500'}],
  \     'audio': [{'src': ''}],
  \     'video': [{'src': ''}],
  \     'image': [{'src': '', 'mode': 'scaleToFill'}],
  \   }
  \ },
  \}
endfunction

function! myspacevim#after() abort

endfunction
