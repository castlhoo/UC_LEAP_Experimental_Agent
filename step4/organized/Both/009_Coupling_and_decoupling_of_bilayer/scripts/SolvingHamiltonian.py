# -*- coding: utf-8 -*-
"""
Created on Wed Jan 27 10:45:20 2021

@author: Icking
"""

import os, sys, glob, re

# path to current working directory. Other paths in the script are defined relative to this path.
cwd                         = os.path.dirname(os.path.realpath(__file__))
#cwd                          = os.path.realpath(__file__)

print(cwd)

import numpy as np
import matplotlib.pyplot as plt
import scipy.linalg as la
import scipy as sp
from scipy import constants
import scipy.linalg as la

##defining constants

g0=3.16*sp.constants.eV   # coupling constants
g1=0.381*sp.constants.eV
g3=0.38*sp.constants.eV
g4=0.14*sp.constants.eV
a=2.46*1E-10 #lattice constant

d0 = 3.35e-10 #layer distance in m
v = 1e6  #in.plane velocity in m/s
eBN = 4   #epsilon of hBN
eBLG = 1   #epsilon of BLG
e0 = sp.constants.epsilon_0   #As/Vm
el = sp.constants.eV  #e in Coulomb
h = sp.constants.h    #h in SI
hbar = sp.constants.hbar   #hbar in SI
me = sp.constants.m_e
DeltaPrime= 0.015*sp.constants.eV

##effective velocities
v0=np.sqrt(3)*a/(2*hbar)*g0
v1=np.sqrt(3)*a/(2*hbar)*g1
v3=np.sqrt(3)*a/(2*hbar)*g3
v4=np.sqrt(3)*a/(2*hbar)*g4


##onsite potential difference

def onPot(D):
    Lambda = d0*el**2*g1 /(2*sp.pi*hbar**2*v**2*e0*eBLG)
    return el*D*d0/2* (1 + Lambda*hbar**2*v**2*e0*D/(el*g1**2) - Lambda*np.log(hbar*v/g1*np.sqrt(sp.pi*e0*D/el)))**(-1)



############################
#defining onsite Potential difference

V=0.1*el

############################

valley =1 #-1
## setting kx and ky

ky=0*np.linspace(-3*np.pi/2/a,3*np.pi/2/a,1)
kx=np.linspace(-3*np.pi/2/a,3*np.pi/2/a,4001)+valley*(4*np.pi/3/a)


Energies=np.array([])
Functions=np.array([])

##setting up the Hamiltonian
## base: A1, B1, A2, B2
## non-dimer: A1 


for i in kx:
    for k in ky:

    ## getting PI and PI_T
    
    
        PI=hbar*(valley*i+k*1j)

        PI_T=hbar*(valley*i-k*1j)

        H0=np.array([
        [V/2+0*1j,v0*PI_T,-v4*PI_T,-v3*PI],
        [v0*PI,(V/2+DeltaPrime)+0*1j,g1+0*1j,-v4*PI_T],
        [-v4*PI,g1+0*1j,-V/2+DeltaPrime+0*1j,g0*PI_T],
        [-v3*PI_T,-v4*PI,v0*PI,-V/2+0*1j]
        ])
        ## Extracting Eigenvalues and Eigenfunction

        eigvals, eigvecs = la.eigh(H0)
        Energies=np.append(Energies,eigvals)
        Functions=np.append(Functions,np.array([i,k,eigvecs]))
        
        
## defining colorscale for scatter plots
## each eigenvalue comes with a vector
## second entry and third entry are non-dimer
LowEn_Val_tL=np.array([])
LowEn_Con_tL=np.array([])

LowEn_Val_bL=np.array([])
LowEn_Con_bL=np.array([])

for i in range(len(kx)):
   
    LowEn_Val_tL=np.append(LowEn_Val_tL,np.square(np.real(Functions[2::3][i][0][2]))+(np.square(np.real(Functions[2::3][i][0][3]))))
    LowEn_Con_tL=np.append(LowEn_Con_tL,np.square(np.real(Functions[2::3][i][3][2]))+(np.square(np.real(Functions[2::3][i][3][3]))))
    
    
    LowEn_Val_bL=np.append(LowEn_Val_bL,np.square(np.real(Functions[2::3][i][0][0]))+(np.square(np.real(Functions[2::3][i][0][1]))))
    LowEn_Con_bL=np.append(LowEn_Con_bL,np.square(np.real(Functions[2::3][i][3][0]))+(np.square(np.real(Functions[2::3][i][3][1]))))
  
### Bottom Layer
fig=plt.figure()
ax= plt.gca()#fig.add_subplot(adjustable='box',aspect='auto')
ax.set_aspect(0.075/0.5*2, adjustable='box')
ax.plot(kx/1E10, Energies[0::4]/el, color='grey') #high energy valence band
ax.scatter(kx/1E10, Energies[1::4]/el,s=LowEn_Val_bL**2.*20,c='gold')#,c=LowEn_Val,marker='.',cmap='autumn_r') #low energy valence band



ax.scatter(kx/1E10, Energies[2::4]/el,s=LowEn_Con_bL**2.*20,c='gold')#,c=LowEn_Con,marker='.',cmap='plasma') #low energy conduction band

ax.plot(kx/1E10, Energies[3::4]/el, color='grey')#high energy conduction band



ax.set_xlim(-0.075,0.075)
ax.set_ylim(-0.5,0.5)    


plt.savefig(os.path.join(cwd,'Hamiltonian.pdf'),  dpi=300, bbox_inches='tight')