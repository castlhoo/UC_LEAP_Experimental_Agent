import numpy as np

sin_30, cos_30 = (1. / 2, np.sqrt(3.) / 2) 
a0 = 2.46 # Honeycomb lattice constant (not nearest-neighbors!) [A]
d0 = 3.35 # Distance between the layers [A]
lcon = a0 / np.sqrt(3) # Nearest neighbor constant [A]
R0 = a0 * cos_30 + lcon * sin_30 + lcon # Lattice constant of graphene with armchair edges
Vppp = -3.09 # Intralayer hopping for graphene [eV]
Vpps =  -0.39 # Interlayer hopping for AA stacked Bilayer graphene[eV]
chem_pot = -0.009070841623338132 # Chemical potential in the scattering region [eV] (Dirac-point energy at the magic angle)
leads_chem_pot = -2 # Chemical potential of the leads [eV]
lambda0 = 0.27 # Constant necessary for the interlayer hoppings[A]