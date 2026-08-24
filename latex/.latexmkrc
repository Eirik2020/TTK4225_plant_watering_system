$pdf_mode = 4;
$out_dir = 'build';
$lualatex = 'lualatex -file-line-error -halt-on-error -interaction=nonstopmode %O %S';
$max_repeat = 5;

@default_files = ('main.tex');

# Files created by packages used in this report.
$clean_ext .= ' run.xml bbl bcf synctex.gz';
