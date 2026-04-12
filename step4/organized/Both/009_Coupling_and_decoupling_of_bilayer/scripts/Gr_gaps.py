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


D_theo=1E6*sp.linspace(-1500,1500,301)


D=np.abs(np.array([-0.7,-0.6,-0.5,-0.4]))
E_gap_pos=np.array([58,45,36,20])
E_gap_pos_error=np.array([1,3,3,3])

E_gap_neg=np.array([50,35,23,15])
E_gap_neg_error=np.array([3,2,2,2])


E_gap_total=(E_gap_pos+E_gap_neg)/2
E_gap_total_error=(E_gap_pos_error*E_gap_pos_error+E_gap_neg_error*E_gap_neg_error)**0.5




plt.errorbar([ 30/39*np.abs(x) for x in D], [y for y in E_gap_total], fmt = '^',color='green', yerr = [y for y in E_gap_total_error], label = 'bias' )



D_57_old = np.genfromtxt(os.path.join(cwd,'Data','DOld.txt'), dtype= 'float', delimiter = ' ')

GapData_57_old = np.genfromtxt(os.path.join(cwd,'Data','oldGaps1e9.txt'), dtype= 'float', delimiter = ' ')


Gap_57_old =GapData_57_old[:,0]
Gap_57_old_error =GapData_57_old[:,1]





D_57_old=np.abs(D_57_old)


plt.errorbar(D_57_old[:]/1000,Gap_57_old[:],yerr=Gap_57_old_error[:], fmt='o',color='black')


plt.xlim(0.,1.2)
plt.ylim(0,140)

plt.legend()


plt.savefig(os.path.join(cwd,'Gr_gaps.pdf'),  dpi=300, bbox_inches='tight')
