reset
set term epslatex standalone color size 3.3, 2.7 font ',14'
set loadpath './'
set out './fig.tex'

set multiplot
unset key

NXPLOTS = 1
NYPLOTS = 1

XSEP = 0.07
YSEP = 0.0

TMARGIN = 0.7
BMARGIN = 0.185
LMARGIN = 0.2
RMARGIN = 0.88

PLOTHEIGHT = (TMARGIN-BMARGIN - (NXPLOTS - 1)*YSEP )/NYPLOTS
PLOTWIDTH = (RMARGIN-LMARGIN - (NYPLOTS - 1)*XSEP )/NXPLOTS 

left_m(i, j) = LMARGIN + i*(PLOTWIDTH + XSEP)
right_m(i, j) = left_m(i, j) + PLOTWIDTH
top_m(i, j) = TMARGIN - j*(PLOTHEIGHT + YSEP)
bottom_m(i, j) = top_m(i, j) - PLOTHEIGHT

#################################################
set palette rgb 34,35,36    #AFM

#set palette rgb 21,22,23    #hot

#set palette rgb 33,13,10     #rainbow


a = -0.12
b = 0.03

i = 0
j = 0

set tmargin at screen top_m(i, j)
set bmargin at screen bottom_m(i, j)
set lmargin at screen left_m(i, j)
set rmargin at screen right_m(i, j)

#set grid
set autoscale

set xrange [0.96:1.04]
set xtics 0.02
set yrange [72 : 80]
set ytics 2


#set format x ''
#unset format x

set key samplen 5.0
set key spacing 1.8

set xlabel offset 0.0, 0.5

set ylabel '$U$ [meV]' 
set xlabel '$n$' 


a = 0.22
b = -0.14

Lx = 0.67
Ly = 0.07
ax = 0.0

set colorbox horizontal
set colorbox user origin left_m(i, j)+ax,top_m(i, j)+0.04 size Lx,Ly

set cblabel offset 0.0, 5.5
set cbtics offset 0.0, 2.5

set cblabel '$|\Delta_{d+id}|$'
set cbtics 0.001

set label  '(c)' at screen left_m(i, j)+b,top_m(i, j)+a

set pm3d
#unset surface
set view map




unset key



splot "data6_cut.dat" u 1:($4*1000):($7/8.48) pt -6


#################################################



