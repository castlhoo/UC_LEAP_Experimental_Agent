reset
set term epslatex standalone color size 5.5, 1.9 font ',12'
set loadpath './'
set out './fig.tex'

set multiplot
unset key

NXPLOTS = 2
NYPLOTS = 1

XSEP = 0.16
YSEP = 0.21

TMARGIN = 0.91
BMARGIN = -0.02
LMARGIN = 0.15
RMARGIN = 0.8

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

set xrange [0.85:1.15]
set xtics 0.1
set yrange [0 : 0.0055]
set ytics 0.002


#set format x ''
#unset format x

set key samplen 2.0
set key spacing 1.2

set ylabel '$\Delta$' 
set xlabel '$n$' 


a = -0.05  #0.09
b = 0.007  #-0.14




set label  '(a)' at screen left_m(i, j)+b,top_m(i, j)+a


set ylabel offset 1.0,0.0
set xlabel offset 0.0,0.5






plot "data6_1_U008.dat" u 1:($7/8.48) w l lt 7 lw 3 t '$\Delta_{d+id}$', "data6_1up_U008.dat" u 1:($7/8.48) w l lt 7 lw 3 t '', "data6_1_U008.dat" u 1:($16/8.48) w l lt 6 lw 3 t '$\Delta_{p-ip}$', "data6_1up_U008.dat" u 1:($16/8.48) w l lt 6 lw 3 t ''


#################################################



i = 1
j = 0

set tmargin at screen top_m(i, j)
set bmargin at screen bottom_m(i, j)
set lmargin at screen left_m(i, j)
set rmargin at screen right_m(i, j)

#set grid
set autoscale

set xrange [0.85:1.15]
set xtics 0.1
set yrange [0 : 0.03]
set ytics 0.01

#set format x ''
#unset format x

set key samplen 5.0
set key spacing 1.8

#set ylabel '$D$' 
set xlabel '$n$' 





set label  '(b)' at screen left_m(i, j)+b,top_m(i, j)+a




plot "data6_101.dat" u 1:($7/8.48) w l lt 7 lw 3 t '', "data6_101up.dat" u 1:($7/8.48) w l lt 7 lw 3 t '', "data6_101_2.dat" u 1:($7/8.48) w l lt 7 lw 3 t '', "data6_101up_2.dat" u 1:($7/8.48) w l lt 7 lw 3 t '', "data6_101.dat" u 1:($16/8.48) w l lt 6 lw 3 t '', "data6_101up.dat" u 1:($16/8.48) w l lt 6 lw 3 t '', "data6_101_2.dat" u 1:($16/8.48) w l lt 6 lw 3 t '', "data6_101up_2.dat" u 1:($16/8.48) w l lt 6 lw 3 t ''


#################################################
#################################################


