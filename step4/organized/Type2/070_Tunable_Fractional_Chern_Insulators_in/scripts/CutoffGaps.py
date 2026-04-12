from LatticePartons import *

#######################################################################################################################################################################
# Gap size vs cutoff
#######################################################################################################################################################################


L = 12
fig, ax = plt.subplots()

# H_21

nx = 2
ny = 2
mux = 7
muy = 7
N_flatbands = 2


Nx,Ny = mux*nx, muy*ny
KX = 2*np.pi*np.arange(mux)/mux
KY = 2*np.pi*np.arange(muy)/muy
KX,KY = np.meshgrid(KX,KY,indexing='ij')

H = mem.cache(HPerp)(N_flatbands,mux,muy,nx,ny)
eigs,_ = np.linalg.eigh(H)
delta_0 = FindGap(eigs)


gaps = []
for r in range(L):
    HCO = cutoff(H,r,Nx,Ny)
    eigs_co,_ = np.linalg.eigh(HCO)
    delta = FindGap(eigs_co)
    gaps.append(delta/delta_0)

ax.plot(np.arange(L),gaps)
ax.scatter(np.arange(L),gaps,label=r"$H'_{21}$",s=7)


# H_22

nx = 2
ny = 2
mux = 9
muy = 9
N_flatbands = 3


Nx,Ny = mux*nx, muy*ny
KX = 2*np.pi*np.arange(mux)/mux
KY = 2*np.pi*np.arange(muy)/muy
KX,KY = np.meshgrid(KX,KY,indexing='ij')

H = mem.cache(HPerp)(N_flatbands,mux,muy,nx,ny)
eigs,_ = np.linalg.eigh(H)
delta_0 = FindGap(eigs)


gaps = []
for r in range(L):
    HCO = cutoff(H,r,Nx,Ny)
    eigs_co,_ = np.linalg.eigh(HCO)
    delta = FindGap(eigs_co)
    gaps.append(delta/delta_0)

ax.plot(np.arange(L),gaps)
ax.scatter(np.arange(L),gaps,label=r"$H'_{22}$",s=7)


# H_33

nx = 6
ny = 2
mux = 4
muy = 12
N_flatbands = 5

Nx,Ny = mux*nx, muy*ny
KX = 2*np.pi*np.arange(mux)/mux
KY = 2*np.pi*np.arange(muy)/muy
KX,KY = np.meshgrid(KX,KY,indexing='ij')

H = mem.cache(HPerp)(N_flatbands,mux,muy,nx,ny)
eigs,_ = np.linalg.eigh(H)
delta_0 = FindGap(eigs)


gaps = []
for r in range(L):
    HCO = cutoff(H,r,Nx,Ny)
    eigs_co,_ = np.linalg.eigh(HCO)
    delta = FindGap(eigs_co)
    gaps.append(delta/delta_0)

ax.plot(np.arange(L),gaps)
ax.scatter(np.arange(L),gaps,label=r"$H'_{33}$",s=7)
ax.invert_xaxis()
ax.set_xlabel(r'$r_{\text{cutoff}}$',fontsize=12)
ax.set_ylabel(r'$\Delta_\text{one-body}$',fontsize=12)
plt.legend(loc='best')

fig.tight_layout()
plt.show()

######################################################################################################################################################################

