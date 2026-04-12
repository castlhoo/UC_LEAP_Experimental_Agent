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



# path to current working directory. Other paths in the script are defined relative to this path.
cwd                         = os.path.dirname(os.path.realpath(__file__))
#cwd                          = os.path.realpath(__file__)

print(cwd)

plt.xlabel(r'D-Field [V/nm]')
plt.ylabel(r'$E_{gap}$ [meV]')
plt.ylim(-5,140)
plt.xlim(-0.05,1.2)

Daa=np.array([-1,-0.9,-0.8,-0.6,-0.4])
E_gap_total = np.array([34.8,30.9,20.6,12.6,0])

E_gap_total_error = E_gap_total*2/100




D_theo=1E6*sp.linspace(0,1500,301)

def gap_theory(x,Offset=0):
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

    D = np.abs(x)

    n=0
    U = el*d0*D/er

    U_old=np.zeros(shape=len(U))
    i=0
    a=np.nanmax(((U-U_old)/el)**2)
    a_old=0


    n_perp=g1**2/(np.pi*hbar**2*v**2)
    Lambda=d0*el**2*n_perp/(2*g1*e0*er)


    while a>=1E-20:
        U_old=U
        a_old=a
        dn=n_perp*U/(2*g1)*np.log(np.abs(n)/2/n_perp+0.5*np.sqrt((n/n_perp)**2+(U/2/g1)**2))
        U = el*d0*D/er+Lambda*g1*dn/n_perp
       
        i=i+1
        a=np.nanmax(((U-U_old)/el)**2)
    
        if a-a_old == 0:
            print('The End')
            break



    return (g1*U / sp.sqrt(g1**2+U**2)   / el)*1000-Offset

popt,pcov=curve_fit(gap_theory, Daa*15/25.5*1E9, E_gap_total, 10, sigma=None)   

bias_fit= np.array([(i > 0) * i for i in gap_theory(D_theo,*popt)])

plt.plot(D_theo/1E9,bias_fit,'--',label=r'Disorder', color='black')
plt.errorbar([ 15/25.5*np.abs(x) for x in Daa], [y for y in E_gap_total], fmt = 'o',color='black', yerr = [y for y in E_gap_total_error], label = 'bias' )




plt.legend()


plt.savefig(os.path.join(cwd,'Au_gap.pdf'),  dpi=300, bbox_inches='tight')
