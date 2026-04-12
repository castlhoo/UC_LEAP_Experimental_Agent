from LatticePartons import *

#####################################################################################################################################################################
# H33 spectrum with momentum sector projection
#####################################################################################################################################################################

fix, ax = plt.subplots(figsize=(3.4,2.1),constrained_layout=True)

N = 10
ns = np.arange(N)

#12 site uc

nx = 6
ny = 2
mux = 1
muy = 2
N_flatbands = 5
filling_fraction = 3/2
n_jobs = 4

Nx,Ny = nx*mux, ny*muy
tau = i*ny/nx
phi = 1/(nx*ny)
lMax = int(LMax(tau,Ny,5))

N_electrons = int(filling_fraction*mux*muy)

parameters = {
    'n_jobs' : n_jobs,
    'nx' : nx, 
    'ny' : ny, 
    'mux' : mux,
    'muy' : muy,
    'N_flatbands' : N_flatbands,
    'filling_fraction' : filling_fraction,
}

eig_dict = mem.cache(DiagonalizeHMB)(number_eigvals=5,**parameters)
eigs = []
for es in eig_dict.values():
    eigs.extend(es)
sparse_eigs = np.sort(eigs)

ax.scatter(ns,sparse_eigs[:N],marker='x',c='blue',label=r'$\phi = 1/12$')

#18 site uc

nx = 6
ny = 3
mux = 1
muy = 2
N_flatbands = 5
filling_fraction = 3/2
n_jobs = 4

Nx,Ny = nx*mux, ny*muy
tau = i*ny/nx
phi = 1/(nx*ny)
lMax = int(LMax(tau,Ny,5))

N_electrons = int(filling_fraction*mux*muy)

parameters = {
    'n_jobs' : n_jobs,
    'nx' : nx, 
    'ny' : ny, 
    'mux' : mux,
    'muy' : muy,
    'N_flatbands' : N_flatbands,
    'filling_fraction' : filling_fraction,
}

eig_dict = mem.cache(DiagonalizeHMB)(number_eigvals=5,**parameters)
eigs = []
for es in eig_dict.values():
    eigs.extend(es)
sparse_eigs = np.sort(eigs)

ax.scatter(ns,sparse_eigs[:N],marker='+',s=50,c='gold',label=r'$\phi = 1/18$')
ax.set_xlabel('Eigenvalue number',fontsize=13)
ax.set_yticks([0,.002,.004,.006])

plt.legend(loc='best')
plt.show()
