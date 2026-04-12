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
##defining constants

milli = 1e-3
#au
nm = 18.8972613
Angstrom = 0.1*nm
Volt = 0.036749322
eV = 0.03674932
ElementaryCharge = 1
Coulomb = 6.2415091*10**18
epsilon_0 = 0.07958
hbar = 1
h = 2*np.pi
alpha =  0.0072973525664
Tesla = 4.25*10**(-6)
c = 1./alpha 
mu_Bohr = 1/2


a_graphene = 2.46*Angstrom 
#McCann Koshino 
gamma_0 = 3.16*eV
gamma_1 = 0.38*eV
gamma_3 = 0.38*eV
gamma_4 = 0.14*eV
Delta = 0.022*eV
Deltas = 0.022*eV

v_F = np.sqrt(3.)/2./hbar*gamma_0*a_graphene
gamma = v_F
v_3 = np.sqrt(3.)/2./hbar*gamma_3*a_graphene
v_4 = np.sqrt(3.)/2./hbar*gamma_4*a_graphene
mass_bilayer = gamma_1/(2*v_F**2)
c0 = 3.35*Angstrom


Vt = 2*Volt
Vb = -2*Volt
Lb = 20*nm
Lt = 20*nm
epsilon_g = 3.22 
epsilon_g = 1
epsilon_hbn = 3.76


#McCann 2013
epsilon_g = 2
n_orth = gamma_1**2/np.pi/hbar**2/v_F**2
Lambda = c0*ElementaryCharge**2*n_orth/2/gamma_1/epsilon_0/epsilon_g
n = epsilon_0*epsilon_hbn*Vb/ElementaryCharge/Lb + epsilon_0*epsilon_hbn*Vt/ElementaryCharge/Lt
Uext = ElementaryCharge*c0/2/epsilon_g*epsilon_hbn*(Vb/Lb-Vt/Lt)


xs = np.linspace(1e-10,2,50) # x Axis from Slizovskiy Fig 7
res1 = []
n=0
for xx in xs:
    x = xx*Volt/nm # x Axis from Slizovskiy Fig 7
    Uext = ElementaryCharge*c0/epsilon_g*x
    Uold = Uext
    for i in range(1000):
        Unew = Uext/( 1 - Lambda/2*np.log( np.abs(n)/2/n_orth + 1/2*np.sqrt( (n/n_orth)**2 + (Uold/2/gamma_1)**2 ) ) )
        Uold = Unew
    res1.append(Unew)


#Slizovskiy 2019 
epsilon_g=1.65
res4 = []
n=0
for xx in xs:
    x = xx*Volt/nm # x Axis from Slizovskiy Fig 7
    Uext = ElementaryCharge*c0/epsilon_g*x
    Uold = Uext
    for i in range(100):
        Unew = Uext/(1 - (1+1/epsilon_g)/2/epsilon_0*n_orth/4/gamma_1*c0*np.log( np.abs(n)/2/n_orth + 1/2*np.sqrt( (n/n_orth)**2 + (Uold/2/gamma_1)**2 ) ) )
        Uold = Unew
    res4.append(Unew)

Ug1 = np.array(res1)*gamma_1/np.sqrt(np.array(res1)**2 + gamma_1**2)/milli/eV
Ug4 = np.array(res4)*gamma_1/np.sqrt(np.array(res4)**2 + gamma_1**2)/milli/eV

plt.plot(xs,Ug1,label="McCann (74), epsilon_BLG=2")
plt.plot(xs,Ug4,label="Slizovskiy, epsilon_BLG=1.65")

#plt.savefig(os.path.join(cwd,'Gap_vs_D.pdf'),  dpi=300, bbox_inches='tight')

plt.show()