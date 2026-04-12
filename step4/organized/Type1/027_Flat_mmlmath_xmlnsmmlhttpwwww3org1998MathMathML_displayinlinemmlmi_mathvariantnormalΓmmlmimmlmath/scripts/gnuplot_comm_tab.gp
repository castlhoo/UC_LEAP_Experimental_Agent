reset
set term epslatex standalone color size 5.6,2.5 font ',12'
set loadpath './'
set out './fig.tex'




set multiplot


NXPLOTS = 2
NYPLOTS = 1

XSEP = 0.17
YSEP = 0.0

TMARGIN = 0.9
BMARGIN = 0.23
LMARGIN = 0.16
RMARGIN = 0.8

PLOTHEIGHT = (TMARGIN-BMARGIN - (NXPLOTS - 1)*YSEP )/NYPLOTS
PLOTWIDTH = (RMARGIN-LMARGIN - (NYPLOTS - 1)*XSEP )/NXPLOTS 

left_m(i, j) = LMARGIN + i*(PLOTWIDTH + XSEP)
right_m(i, j) = left_m(i, j) + PLOTWIDTH
top_m(i, j) = TMARGIN - j*(PLOTHEIGHT + YSEP)
bottom_m(i, j) = top_m(i, j) - PLOTHEIGHT

#################################################

i = 0
j = 0

set tmargin at screen top_m(i, j)
set bmargin at screen bottom_m(i, j)
set lmargin at screen left_m(i, j)
set rmargin at screen right_m(i, j)

set border lc "black" lw 2.5

set autoscale

p = 3.14159265359

a = 0.03
b = -0.151

set xrange [0.05:0.9]
set yrange [p-p/2:p]
set xtics 0.2
set ytics 1
#set cbtics 0.00002

set ytics ('$\pi/2$' p/2, '$5\pi/8$' 5*p/8, '$3\pi/4$' 3*p/4, '$7\pi/8$' 7*p/8,'$\pi$' p)

set key samplen 2.5
set key spacing 1.2


set ylabel offset 0.,0.

set ylabel '$|t|$ [meV]' 
set xlabel '$D$ [V/nm]' 


set label  '(a)' at screen left_m(i, j)+b,top_m(i, j)+a



set ylabel '$\phi$' 
set xlabel '$D$ [V/nm]' 




plot "Ddata.dat" u 1:3 w lp lw 3 pt 5 lc 0 t ''







#################################################

i = 1
j = 0

set tmargin at screen top_m(i, j)
set bmargin at screen bottom_m(i, j)
set lmargin at screen left_m(i, j)
set rmargin at screen right_m(i, j)

set autoscale

set xrange [0.4:1.6]
set yrange [0:250]
set xtics 0.4
set ytics 100
#set cbtics 0.00002

#set ytics ('$\frac{\pi}{2}$' p/2, '$\frac{3\pi}{4}$' 3*p/4,'$\pi$' p)

#set ytics ('$\pi/2$' p/2, '$5\pi/8$' 5*p/8, '$3\pi/4$' 3*p/4, '$7\pi/8$' 7*p/8,'$\pi$' p)


set key samplen 2.5
set key spacing 1.2

set ylabel offset 1.,0

set ylabel 'DOS [a.u]' 
set xlabel '$n$' 





set label  '(b)' at screen left_m(i, j)+b,top_m(i, j)+a



plot "dos_1.dat" u 5:($4/3e6) w l lc 0 lw 3 t '', "dos_6.dat" u 5:($4/3e6) w l lc 0 lw 3 t '', "dos-0.6.dat" u 3:2 w l lc 0 lw 3 t '', "dos-0.2.dat" u 3:2 w l lc 0 lw 3 t '', "dos_9.dat" u 5:4 w l lc 0 lw 3 t ''




#################################################






