from LatticePartons import * 



########################################################################################################################################################################
# H21 and H22 ground states K resolved
########################################################################################################################################################################

fig, ax = plt.subplots(figsize=(3.4, 2.6))

n_jobs = 1 
nx = 2
ny = 2
mux = 3
muy = 2 
N_flatbands = 2
filling_fraction = 2/3

Nx,Ny = nx*mux, ny*muy
tau = i*ny/nx
phi = 1/(nx*ny)
lMax = int(LMax(tau,Ny,5))

parameters = {
    'n_jobs' : n_jobs,
    'nx' : nx, 
    'ny' : ny, 
    'mux' : mux,
    'muy' : muy,
    'N_flatbands' : N_flatbands,
    'filling_fraction' : filling_fraction
}

N = 10
xs = np.arange(N)

H = mem.cache(ManyBodyHPerp)(**parameters)
eig_dict = DiagonalizeHMB(H=H,**parameters)
eigs = []
for es in eig_dict.values():
    eigs.extend(es)
sparse_eigs = np.sort(eigs)

ax.scatter(xs,sparse_eigs[:N],c='blue',marker='x',label=r'$H_{21}$')

n_jobs = 1
nx = 2
ny = 2
mux = 2
muy = 3
N_flatbands = 3
filling_fraction = 1

Nx,Ny = nx*mux, ny*muy
tau = i*ny/nx
phi = 1/(nx*ny)
lMax = int(LMax(tau,Ny,5))

parameters = {
    'n_jobs' : n_jobs,
    'nx' : nx, 
    'ny' : ny, 
    'mux' : mux,
    'muy' : muy,
    'N_flatbands' : N_flatbands,
    'filling_fraction' : filling_fraction
}

N = 10
xs = np.arange(N)

H = mem.cache(ManyBodyHPerp)(**parameters)
eig_dict = DiagonalizeHMB(H=H,**parameters)
eigs = []
for es in eig_dict.values():
    eigs.extend(es)
sparse_eigs = np.sort(eigs)

ax.scatter(xs,sparse_eigs[:N],c='gold',marker='+',label=r'$H_{22}$')
ax.set_xlabel('Eigenvalue number',fontsize=13)
ax.set_ylabel('Eigenvalue',fontsize=13)
ax.legend()
plt.tight_layout()
plt.show()




########################################################################################################################################################################
# H_21 quasi-hole spectra
########################################################################################################################################################################
fig, ax = plt.subplots(figsize=(3.4, 2.6))

n_jobs = 1
nx = 5
ny = 1
mux = 1
muy = 7
N_flatbands = 2
filling_fraction = 2/3

Nx, Ny = nx*mux, ny*muy

parameters = {
    'n_jobs' : n_jobs,
    'nx' : nx, 
    'ny' : ny, 
    'mux' : mux,
    'muy' : muy,
    'N_flatbands' : N_flatbands,
    'filling_fraction' : filling_fraction,
}


N = 45
xs = np.arange(N)

H = mem.cache(ManyBodyHPerp)(**parameters)
eig_dict = DiagonalizeHMB(H=H,**parameters)

eig_list = []
for A in range(mux):
    for B in range(muy):
        eig_list.extend(eig_dict[(A,B)])
eig_list = np.sort(eig_list)

ax.scatter(xs,eig_list[:N])
ax.set_xlabel('Eigenvalue number',fontsize=13)
ax.set_ylabel('Eigenvalue',fontsize=13)
plt.tight_layout()
plt.show()


