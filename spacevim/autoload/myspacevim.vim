function! myspacevim#before() abort
    let g:loaded_python_provider=1
    " let g:python2_host_prog = '/opt/homebrew/bin/python3'
    let g:python3_host_prog='/opt/homebrew/bin/python3'
    set pyxversion=3

    "key mapping
    inoremap jj <esc>
    set clipboard+=unnamedplus
    "逗号后空格
    inoremap , ,<Space>
    "等号左右空格
    " inoremap=<Space>=<Space>
    nmap <silent> <A-k> :wincmd k<CR>
    nmap <silent> <A-j> :wincmd j<CR>
    nmap <silent> <A-h> :wincmd h<CR>
    nmap <silent> <A-l> :wincmd l<CR>

    " SimpylFold
    let g:SimpylFold_docstring_preview = 1

    "ale
    let g:ale_linters={
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
    let g:snips_author = "杨浩"
    let g:snips_email = "yh392261226@gmail.com"
    let g:snips_github = "https://github.com/yh392261226"

    " automately add the file head for alpertuna/vim-header
    let g:header_auto_add_header = 0
    let g:header_field_modified_timestamp = 0
    let g:header_field_author = '杨浩'
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




    " Find files using Telescope command-line sugar.
    nnoremap <leader>ff <cmd>Telescope find_files<cr>
    nnoremap <leader>fg <cmd>Telescope live_grep<cr>
    nnoremap <leader>fb <cmd>Telescope buffers<cr>
    nnoremap <leader>fh <cmd>Telescope help_tags<cr>

    " Using Lua functions
    nnoremap <leader>ff <cmd>lua require('telescope.builtin').find_files()<cr>
    nnoremap <leader>fg <cmd>lua require('telescope.builtin').live_grep()<cr>
    nnoremap <leader>fb <cmd>lua require('telescope.builtin').buffers()<cr>
    nnoremap <leader>fh <cmd>lua require('telescope.builtin').help_tags()<cr>
endfunction

function! myspacevim#after() abort
  if executable('intelephense')
    augroup LspPHPIntelephense
      au!
      au User lsp_setup call lsp#register_server({
          \ 'name': 'intelephense',
          \ 'cmd': {server_info->[&shell, &shellcmdflag, 'intelephense --stdio']},
          \ 'whitelist': ['php'],
          \ 'initialization_options': {'storagePath': '/tmp/intelephense'},
          \ 'workspace_config': {
          \   'intelephense': {
          \     'files': {
          \       'maxSize': 1000000,
          \       'associations': ['*.php', '*.phtml'],
          \       'exclude': [],
          \     },
          \     'completion': {
          \       'insertUseDeclaration': v:true,
          \       'fullyQualifyGlobalConstantsAndFunctions': v:false,
          \       'triggerParameterHints': v:true,
          \       'maxItems': 100,
          \     },
          \     'format': {
          \       'enable': v:true
          \     },
          \   },
          \ }
          \})
    augroup END
  endif

  " Use tab for trigger completion with characters ahead and navigate.
  " NOTE: Use command ':verbose imap <tab>' to make sure tab is not mapped by
  " other plugin before putting this into your config.
  inoremap <silent><expr> <TAB>
        \ pumvisible() ? "\<C-n>" :
        \ <SID>check_back_space() ? "\<TAB>" :
        \ coc#refresh()
  inoremap <expr><S-TAB> pumvisible() ? "\<C-p>" : "\<C-h>"

  function! s:check_back_space() abort
    let col = col('.') - 1
    return !col || getline('.')[col - 1]  =~# '\s'
  endfunction

  " Use <c-space> to trigger completion.
  inoremap <silent><expr> <c-space> coc#refresh()

  " Use <cr> to confirm completion, `<C-g>u` means break undo chain at current
  " position. Coc only does snippet and additional edit on confirm.
  " <cr> could be remapped by other vim plugin, try `:verbose imap <CR>`.
  if exists('*complete_info')
    inoremap <expr> <cr> complete_info()["selected"] != "-1" ? "\<C-y>" : "\<C-g>u\<CR>"
  else
    inoremap <expr> <cr> pumvisible() ? "\<C-y>" : "\<C-g>u\<CR>"
  endif

  " Use `[g` and `]g` to navigate diagnostics
  nmap <silent> [g <Plug>(coc-diagnostic-prev)
  nmap <silent> ]g <Plug>(coc-diagnostic-next)

  " GoTo code navigation.
  nmap <silent> gd <Plug>(coc-definition)
  nmap <silent> gy <Plug>(coc-type-definition)
  nmap <silent> gi <Plug>(coc-implementation)
  nmap <silent> gr <Plug>(coc-references)

  " Use K to show documentation in preview window.
  nnoremap <silent> K :call <SID>show_documentation()<CR>

  function! s:show_documentation()
    if (index(['vim','help'], &filetype) >= 0)
      execute 'h '.expand('<cword>')
    else
      call CocAction('doHover')
    endif
  endfunction

  " Highlight the symbol and its references when holding the cursor.
  autocmd CursorHold * silent call CocActionAsync('highlight')

  " Symbol renaming.
  nmap <leader>rn <Plug>(coc-rename)

  " Formatting selected code.
  xmap <leader>f  <Plug>(coc-format-selected)
  nmap <leader>f  <Plug>(coc-format-selected)

  augroup mygroup
    autocmd!
    " Setup formatexpr specified filetype(s).
    autocmd FileType typescript,json setl formatexpr=CocAction('formatSelected')
    " Update signature help on jump placeholder.
    autocmd User CocJumpPlaceholder call CocActionAsync('showSignatureHelp')
  augroup end

  " Applying codeAction to the selected region.
  " Example: `<leader>aap` for current paragraph
  xmap <leader>a  <Plug>(coc-codeaction-selected)
  nmap <leader>a  <Plug>(coc-codeaction-selected)

  " Remap keys for applying codeAction to the current line.
  nmap <leader>ac  <Plug>(coc-codeaction)
  " Apply AutoFix to problem on the current line.
  nmap <leader>qf  <Plug>(coc-fix-current)

  " Introduce function text object
  " NOTE: Requires 'textDocument.documentSymbol' support from the language server.
  xmap if <Plug>(coc-funcobj-i)
  xmap af <Plug>(coc-funcobj-a)
  omap if <Plug>(coc-funcobj-i)
  omap af <Plug>(coc-funcobj-a)

  " Use <TAB> for selections ranges.
  " NOTE: Requires 'textDocument/selectionRange' support from the language server.
  " coc-tsserver, coc-python are the examples of servers that support it.
  nmap <silent> <TAB> <Plug>(coc-range-select)
  xmap <silent> <TAB> <Plug>(coc-range-select)

  " Add `:Format` command to format current buffer.
  command! -nargs=0 Format :call CocAction('format')

  " Add `:Fold` command to fold current buffer.
  command! -nargs=? Fold :call     CocAction('fold', <f-args>)

  " Add `:OR` command for organize imports of the current buffer.
  command! -nargs=0 OR   :call     CocAction('runCommand', 'editor.action.organizeImport')

  " Add (Neo)Vim's native statusline support.
  " NOTE: Please see `:h coc-status` for integrations with external plugins that
  " provide custom statusline: lightline.vim, vim-airline.
  set statusline^=%{coc#status()}%{get(b:,'coc_current_function','')}

  " Mappings using CoCList:
  " Show all diagnostics.
  nnoremap <silent> <space>a  :<C-u>CocList diagnostics<cr>
  " Manage extensions.
  nnoremap <silent> <space>e  :<C-u>CocList extensions<cr>
  " Show commands.
  nnoremap <silent> <space>c  :<C-u>CocList commands<cr>
  " Find symbol of current document.
  nnoremap <silent> <space>o  :<C-u>CocList outline<cr>
  " Search workspace symbols.
  nnoremap <silent> <space>s  :<C-u>CocList -I symbols<cr>
  " Do default action for next item.
  nnoremap <silent> <space>j  :<C-u>CocNext<CR>
  " Do default action for previous item.
  nnoremap <silent> <space>k  :<C-u>CocPrev<CR>
  " Resume latest coc list.
  nnoremap <silent> <space>p  :<C-u>CocListResume<CR>

endfunction
