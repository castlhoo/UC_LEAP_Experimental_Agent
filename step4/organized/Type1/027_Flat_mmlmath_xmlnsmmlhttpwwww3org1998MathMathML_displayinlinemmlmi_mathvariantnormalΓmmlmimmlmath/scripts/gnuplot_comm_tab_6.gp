reset
set term epslatex standalone color size 3.0, 7.0 font ',14'
set loadpath './'
set out './fig.tex'

set multiplot
unset key

NXPLOTS = 1
NYPLOTS = 2

XSEP = 0.0
YSEP = 0.24

TMARGIN = 0.87
BMARGIN = 0.36
LMARGIN = 0.255
RMARGIN = 0.9

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
#set ytics 100

#set format x ''
#unset format x

set key samplen 5.0
set key spacing 1.8

set ylabel '$D$ [V/nm]' 
set xlabel '$n$' 

Lx = 0.64
ax = 0.0
set colorbox horizontal
set colorbox user origin left_m(i, j)+ax,top_m(i, j)+0.015 size Lx,0.022

set cblabel offset 0.0, 5.5
set cbtics offset 0.0, 2.5


set cblabel '$|\Delta_{d+id}|$'
set cbtics 0.002

set pm3d
#unset surface
set view map

#set label  '(a)' at screen left_m(i, j)+a,top_m(i, j)+b

set ylabel offset -0.5,0.2
unset key

splot "data6_V_681.dat" u 1:2:($7/8.48) pt -6, "data6_V_681up.dat" u 1:2:($7/8.48) pt -6, "dos.dat" u 1:2:(0) w l lw 8 lc 3



#################################################

a = -0.12
b = 0.03

i = 0
j = 1

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

set format x ''
unset format x

set key samplen 5.0
set key spacing 1.8

set ylabel '$D$ [V/nm]' 
set xlabel '$n$' 



ax = 0.0
set colorbox horizontal
set colorbox user origin left_m(i, j)+ax,top_m(i, j)+0.015 size Lx,0.022

set cblabel offset 0.0, 5.5
set cbtics offset 0.0, 2.5


set cblabel '$|\Delta_{p-ip}|$'
set cbtics 0.00125

set pm3d
#unset surface
set view map

#set label  '(b)' at screen left_m(i, j)+a,top_m(i, j)+b

set ylabel offset -0.5,0.2
unset key

splot "data6_V_681.dat" u 1:2:($16/8.48) pt -6, "data6_V_681up.dat" u 1:2:($16/8.48) pt -6, "dos.dat" u 1:2:(0) w l lw 8 lc 3

#################################################

