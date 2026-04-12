# -*- coding: utf-8 -*-
"""
Created on Wed Jan 27 10:45:20 2021

@author: Icking
"""
from matplotlib import cm
import matplotlib.colors as colors
import numpy as np
import scipy as sp
from matplotlib import rcParams
import os, sys, glob, re
from typing import Type
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LogNorm
from numpy.core.numeric import False_, indices
from scipy.optimize.zeros import bisect
import scipy as sp
from scipy.optimize import curve_fit
import pyqtgraph as pg
from qcodes.plots.pyqtgraph import QtPlot 
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import rc


def fit(bias,dIdV=1E-10,offset=1E-12):
    return dIdV*bias+offset

# path to current working directory. Other paths in the script are defined relative to this path.
cwd                         = os.path.dirname(os.path.realpath(__file__))
#cwd                          = os.path.realpath(__file__)

print(cwd)

bias1= np.genfromtxt(os.path.join(cwd,'Data','Au_D-250mVnm_bias.txt'), dtype= 'float', delimiter = '\n')


Delta_TG=np.genfromtxt(os.path.join(cwd,'Data','Au_D-250mVnm_topgate.txt'), dtype= 'float', delimiter = '\n')

Delta_BG=np.genfromtxt(os.path.join(cwd,'Data','Au_D-250mVnm_bottomgate.txt'), dtype= 'float', delimiter = '\n')


I_A1=1E-6*np.genfromtxt(os.path.join(cwd,'Data','Au_D-250mVnm_current.txt'), dtype= 'float')






# numerical calculation od dI/dV

dIdV = np.zeros(shape=(201,201))


i=0
p0=[3E-4,-1E-7]    
for i in range(0,201):
    m = np.array([])
    for j in range(3,201):
        popt,pcov=curve_fit(fit, bias1[j-1:j+1],I_A1[j-1:j+1,i],p0)
        m=np.append(m,popt[0])

        d=11-j
    dIdV[3::,i]=m[::]
    dIdV[0:2,i] = np.diff(I_A1[0:3,i])/np.diff(bias1[0:3])
    ### The next few lines may seem strange, but due to noise we get some negative contribution to
    ### dI/dV, which appear as "holes" in the logarithmic scale. As they stem from noise we filter them
    ### out by taking the next neighbour with dI/dV[j,i]>0. This does not have a significant effect on the size of the gap,
    ### because at the edges the current is high enough to be not affected as strongly by noise as in the gap.

    for j in range(0,200):
        if dIdV[j,i]*25800<=0.1E-5:
            dIdV[j,i]=(dIdV[j-1,i]+dIdV[j+1,i])/2
    for j in range(0,200):
        if dIdV[j,i]*25800<=0.1E-5:
            dIdV[j,i]=(dIdV[j-1,i]+dIdV[j+1,i])/2
        j=j+1

 ## Theorie_value
e=1.6E-19;
hbar=1.05E-34
gamma1=0.39*e
eps0=8.85E-12
C=2*eps0/0.335E-9
v=0.8E6

D_theo=-0.25*1E9

d0 = 3.35e-10 #layer distance in m
g1 = 0.39*sp.constants.eV    #hopping parameter in J
v = 1e6  #in.plane velocity in m/s
eBN = 4   #epsilon of hBN
eBLG = 1.13   #epsilon of BLG
e0 = sp.constants.epsilon_0   #As/Vm
el = sp.constants.eV  #e in Coulomb
h = sp.constants.h    #h in SI
hbar = sp.constants.hbar   #hbar in SI


er=2

D = np.abs(D_theo)

n=0#e0*D/el
U = el*d0*D/er#+d0*el**2/(e0*2)*(n)/er

U_old=0
i=0
a=np.nanmax(((U-U_old)/el)**2)
a_old=0


#for i in range(100):
while a>=1E-20:
    U_old=U
    a_old=a
    n=g1*U/(2*np.pi*hbar**2*v**2)*np.log(4*g1/U)
    U = el*d0*D/er-d0*el**2/(e0*2)*(n)/er
    #print('yolo',i,a)
    i=i+1
    a=np.nanmax(((U-U_old)/el)**2)
    
    if a-a_old == 0:
        print('The End')
        break

Eg3=g1*U / sp.sqrt(g1**2+U**2)   / el


E_gap_theo = Eg3

# calculating effective gating voltage
beta= 1/0.99
VG0=0.24
Vg=(Delta_TG+Delta_BG/beta)/(1+1/beta)-VG0

#plotting the data


plt.clf()
ax = plt.gca()
ax.set_aspect(70/100*2, adjustable='box')

plt.title(f'D-Field = -0.25 V/nm')
plt.axhline(E_gap_theo*1000,linestyle='--',color='w')
plt.axhline(-E_gap_theo*1000,linestyle='--',color='w')



# Laden der gespeicherten colorscale:
gradient = np.load(r"CS_colorscale_Diamanten2.npy",allow_pickle=True)[0]
# Pyqtgraph Gradient Widget erzeugen und einstellungen laden
gedit = pg.GradientWidget()
gedit.restoreState(gradient)
# Lookup table erstellen
lut = gedit.getLookupTable(256)
# Matplotlib colormap erstellen
mcolors = np.array([x for x in lut]) / 255.
c = colors.ListedColormap(mcolors)    



plt.pcolormesh(Vg*1000, bias1*1000,25813*(dIdV),cmap=c,shading='gouraud',norm=colors.LogNorm(vmin=1E-6,vmax=1E1))





plt.xlim(-70,70)
plt.ylim(-100,100)

cbar=plt.colorbar()
cbar.set_label('R ($\Omega$)', rotation=90,labelpad =15)
plt.xlabel('$V_g$ (mV)')
plt.ylabel('$V_{bias}(mV)$')

plt.savefig(os.path.join(cwd,'Figures','AuPlot_250D_2.pdf'),  dpi=300,bbox_inches='tight' )