reset
set term epslatex standalone color size 5.5, 2.7 font ',14'
set loadpath './'
set out './fig.tex'

set multiplot
unset key

NXPLOTS = 2
NYPLOTS = 1

XSEP = 0.07
YSEP = 0.0

TMARGIN = 0.7
BMARGIN = 0.185
LMARGIN = 0.15
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

set xrange [0.8:1.2]
set xtics 0.2
set yrange [0 : 0.6]
set ytics 0.2


#set format x ''
#unset format x

set key samplen 5.0
set key spacing 1.8

set xlabel offset 0.0, 0.5

set ylabel '$D$ [V/nm]' 
set xlabel '$n$' 


a = 0.22
b = -0.14

Lx = 0.36
Ly = 0.06
ax = 0.0

set colorbox horizontal
set colorbox user origin left_m(i, j)+ax,top_m(i, j)+0.04 size Lx,Ly

set cblabel offset 0.0, 5.5
set cbtics offset 0.0, 2.5

set cblabel '$g_v^2$'
set cbtics 0.08

set label  '(a)' at screen left_m(i, j)+b,top_m(i, j)+a

set pm3d
#unset surface
set view map




unset key



splot "data3_V_681.dat" u 1:2:($29*$29) pt -6, "data3_V_681up.dat" u 1:2:($29*$29) pt -6, "dos.dat" u 1:2:(0.28) w l lw 8 lc 3


#################################################
#################################################
set palette rgb 34,35,36    #AFM

#set palette rgb 21,22,23    #hot

#set palette rgb 33,13,10     #rainbow


a = 0.22
b = 0.03

i = 1
j = 0

set tmargin at screen top_m(i, j)
set bmargin at screen bottom_m(i, j)
set lmargin at screen left_m(i, j)
set rmargin at screen right_m(i, j)

#set grid
set autoscale

set xrange [0.8:1.2]
set xtics 0.2
set yrange [0 : 0.6]
set ytics 0.2
#set ytics 100

set format y ''
#unset format x

set key samplen 5.0
set key spacing 1.8

unset ylabel
#set ylabel '$D$ [V/nm]' 
#unset xlabel


ax = 0.0
set colorbox horizontal
set colorbox user origin left_m(i, j)+ax,top_m(i, j)+0.04 size Lx,Ly

set cblabel offset 0.0, 5.5
set cbtics offset 0.0, 2.5



set cblabel '$\lambda_s^4$'
set cbtics 0.2

set pm3d
#unset surface
set view map


a = 0.24
b = -0.06

set label  '(b)' at screen left_m(i, j)+b,top_m(i, j)+a

set ylabel offset -0.3,0.2
unset key

splot "data3_V_681.dat" u 1:2:($26*$26*$26*$26) pt -6, "data3_V_681up.dat" u 1:2:($26*$26*$26*$26) pt -6, "dos.dat" u 1:2:(2.2) w l lw 8 lc 3



#################################################


