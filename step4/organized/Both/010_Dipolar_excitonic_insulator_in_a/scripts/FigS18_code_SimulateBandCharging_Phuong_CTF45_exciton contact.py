# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 18:04:09 2020

@author: malg
"""


import numpy as np
from pylab import *
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import BoundaryNorm
from scipy.optimize import fsolve,leastsq

import operator
import scipy
from scipy import integrate
import time as time
from scipy import signal
import sys

mpl.rcParams['font.size']=18
mpl.rcParams['legend.fontsize']=10
mpl.rcParams['lines.linewidth']=1.5
mpl.rcParams['figure.figsize']=(6,6)
mpl.rcParams['xtick.major.size']=5
mpl.rcParams['ytick.major.size']=5
mpl.rcParams['font.family']='Arial'
mpl.rcParams['mathtext.fontset'] = "stixsans"

#f=plt.figure()
def savetext(X,Y,Zappendlist,filename):
    # generate a table using X as col index and Y as row index
    data=[]
    y1=np.expand_dims(Y,0)
    y1=np.vstack((y1,Zappendlist))
    x1=np.hstack((np.array([0]),X))
    x1=np.expand_dims(x1,1)
    data=np.hstack((x1,y1))
    np.savetxt(filename, np.transpose(data), delimiter=',')
def Q_W(V):
    val=abs(V)-abs(Gap/2)#0.849#
#    val=abs(V)
    if val<0:return 0
    else: return C_Q*val*sign(V)
def Q_M(V):
    val=abs(V)-abs(Gap/2)#0.759#
#    val=abs(V)
    if val<0:return 0
    else: return C_Q*val*sign(V)
def f(x):
    V1=float(x[0])
    V2=float(x[1])
    return np.array([
            (V1-(-D+Gate))*C1+(V1-V2)*Ci+Q_W(V1-0),
            (V2-V1)*Ci+Q_M(V2+Bias)+(V2-(D+Gate))*C2
            ])
def get_n(initial=[0.1,0.1]):
    x0 = initial #initial try parameters
    result = fsolve(f,x0)
    V1=result[0]
    V2=result[1]
    n=np.zeros(2)
    n[0]=Q_W(V1)
    n[1]=Q_M(V2+Bias)
    return n
def line(Vb):
    VB=-0.39
    CB=0.135 
    Vg=((CB+VB)-Vb)/2
    return np.round(Vg,5) 

if __name__ == '__main__':
    donoting=0
    #%% plot spectra
    pi=3.1415
    hbar=1.05e-34
    me=0.5*9.109e-31
    epsilon0=8.85e-12
    qe=1.6e-19
    D = 11/2
    C1=3.5*epsilon0/10.9e-9 # capacitor for bot gate
    Ci=3.5*epsilon0/10e-9 # barrier thickness + 0.3nm. 7 layer, may be 6 layer
    C2=3.5*epsilon0/10.36e-9 # capacitor for top gate
    C_Q=qe**2*me/(hbar**2*pi)#E=hbar^2*pi*n/(2*me)
    Gap=1.51 #interlayer gap
    
    plt.close('all')
    if True:
        Gatelist = np.linspace(-0.5,-0.249,301)
        Biaslist = np.linspace(0.35,0.6,301)
        n_W=np.zeros((len(Gatelist),len(Biaslist)))
        n_M=np.zeros((len(Gatelist),len(Biaslist)))
        Cp=np.zeros((len(Gatelist),len(Biaslist)))
        gates=np.zeros((len(Gatelist),len(Biaslist)))
        biass=np.zeros((len(Gatelist),len(Biaslist)))
        for i in range(len(Gatelist)):
            Gate=Gatelist[i]
            for j in range(len(Biaslist)):
                Bias=Biaslist[j]
                n=(get_n()+get_n(initial=[0.2,0.2]))/2 #get_n twice with diff inital to confirm simulation
                n_W[i,j]=n[0]
                n_M[i,j]=n[1]
                if abs(n[0])>0: Cp[i,j]=Cp[i,j]+1
                if abs(n[1])>0: Cp[i,j]=Cp[i,j]+1
                gates[i,j]=Gate+0.39
                biass[i,j]=Bias
                
    #%% plot
        fig1=plt.figure(1)
        ax=plt.subplot(111)
        cont=ax.pcolormesh(gates,biass,Cp,
                           vmax=5,vmin=-0,
    #                   norm=colors.LogNorm(),
                       cmap='bone_r')
        plt.xlabel('$\mathregular{V_g}$ (V)')
        plt.ylabel('$\mathregular{V_b}$ (V)')
        plt.ylim([0.35,0.6])
        plt.xlim([-0.095,0.14])
    #    plt.yticks([-0.55,-0.60,-0.65,-0.70,-0.75])
        plt.yticks(np.arange(0.35,0.61,0.05))
        plt.tight_layout()
        ax.set_aspect(1.0, 'box')
        
#        plt.plot(line0(Biaslist),Biaslist)
        
#        #Plot the equal line
        # lineVg=np.zeros(len(Biaslist))
        # for j in range(len(Biaslist)):
        #     Bias=Biaslist[j]
        #     lineVg[j]=line(Bias)+0.39
        # plt.plot(lineVg,Biaslist)
#    

    nWequal=np.zeros(len(Biaslist))
    nMequal=np.zeros(len(Biaslist))
    for j in range(len(Biaslist)):
            Bias=Biaslist[j]
            Gate=line(Bias)
            print(Bias)
            print(Gate)
            n=(get_n()+get_n(initial=[0.2,0.2]))/2 #get_n twice with diff inital to confirm simulation
            nWequal[j]=(n[0]/qe)*1e-4 #unit cm^-2
            nMequal[j]=(n[1]/qe)*1e-4 #unit cm^-2 
    fig2=plt.figure(2)
    plt.subplot(1, 1, 1)
    plt.plot(Biaslist,nWequal,label='p in WSe2')
    plt.plot(Biaslist,nMequal,label='n in MoSe2')
    plt.xlim([0.4,0.6])
    plt.legend()
    # plt.subplot(1, 2, 2)
    # plt.plot(Biaslist,nWequal+nMequal,label='n-p')
    # plt.xlim([0,0.9])
    # plt.legend()
    
    
    
#    fig3=plt.figure(3)
    
#    plt.plot(Gatelist,n_M[:,0])
#    plt.plot(Gatelist,n_M[:,0])
#    fig2=plt.figure()
#    plt.plot(Gatelist,n_W[:,0])
#    plt.plot(Gatelist,n_M[:,0])
#    plt.plot(Gatelist,Cp[:,0])

    
        
        
    

#    plt.colorbar(cont,fraction=0.04,label='Cp (uV)')
