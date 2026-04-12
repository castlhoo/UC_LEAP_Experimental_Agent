gnuplot gnuplot_comm_tab.gp -"set loadpath '..\'"
latex fig.tex
dvips fig.dvi
ps2pdf fig.ps
convert -flatten -density 700 fig.pdf fig.png
