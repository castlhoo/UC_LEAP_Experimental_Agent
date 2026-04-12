from LatticePartons import *



#######################################################################################################################################################################
# H21 H22 H33 band structures + cutoffs
#######################################################################################################################################################################
def computeEigData(oracle,H,mux,muy,nx,ny):
    eig_data = np.zeros((mux,muy,nx*ny))
    for alpha in range(mux):
        for beta in range(muy):
            basis, _ = np.linalg.qr(oracle[alpha,beta].T,mode='reduced')
            Hab = (basis.conj().T)@H@basis
            eig_data[alpha,beta] = np.sort(np.real(np.linalg.eigvals(Hab)))
    e_min, e_max = np.min(eig_data), np.max(eig_data) 
    eig_data = eig_data - e_min
    return eig_data, e_min, e_max

fig, axes = plt.subplots(2,3,subplot_kw={"projection": "3d"},constrained_layout=True,figsize=(3.4, 2.1))

# H_21

n_jobs = 4
nx = 3
ny = 1
mux = 20
muy = 20
N_flatbands = 2
filling_fraction = 2/3
r_cutoff = 3

Nx,Ny = mux*nx, muy*ny
KX_21 = 2*np.pi*np.arange(mux)/mux
KY_21 = 2*np.pi*np.arange(muy)/muy
KX_21,KY_21 = np.meshgrid(KX_21,KY_21,indexing='ij')

oracle = mem.cache(PsiOracle)(nx*ny,mux,muy,nx,ny).reshape((mux,muy,nx*ny,mux*nx*muy*ny))
H = mem.cache(HPerp)(N_flatbands,mux,muy,nx,ny)
HCO = cutoff(H,r_cutoff,Nx,Ny)

eig_data_21, e_min_21, e_max_21 = computeEigData(oracle,H,mux,muy,nx,ny)
eig_data_co_21, e_min_co_21, e_max_co_21 = computeEigData(oracle,HCO,mux,muy,nx,ny)

lower_bands = eig_data_co_21[:,:,:N_flatbands]
upper_bands = eig_data_co_21[:,:,N_flatbands:]

Delta_21 = upper_bands.min() - lower_bands.max()
w_21 = lower_bands.max() - lower_bands.min()

# H_22

n_jobs = 4
nx = 2
ny = 2
mux = 20
muy = 20
N_flatbands = 3
filling_fraction = 1
r_cutoff = 4 

Nx,Ny = mux*nx, muy*ny
KX_22 = 2*np.pi*np.arange(mux)/mux
KY_22 = 2*np.pi*np.arange(muy)/muy
KX_22,KY_22 = np.meshgrid(KX_22,KY_22,indexing='ij')

oracle = mem.cache(PsiOracle)(nx*ny,mux,muy,nx,ny).reshape((mux,muy,nx*ny,mux*nx*muy*ny))
H = mem.cache(HPerp)(N_flatbands,mux,muy,nx,ny)
HCO = cutoff(H,r_cutoff,Nx,Ny)

eig_data_22, e_min_22, e_max_22 = computeEigData(oracle,H,mux,muy,nx,ny)
eig_data_co_22, e_min_co_22, e_max_co_22 = computeEigData(oracle,HCO,mux,muy,nx,ny)

lower_bands = eig_data_co_22[:,:,:N_flatbands]
upper_bands = eig_data_co_22[:,:,N_flatbands:]

Delta_22 = upper_bands.min() - lower_bands.max()
w_22 = lower_bands.max() - lower_bands.min()


# H_33

n_jobs = 4
nx = 6
ny = 2
mux = 4
muy = 12
N_flatbands = 5
filling_fraction = 3/2
r_cutoff = 8

Nx,Ny = mux*nx, muy*ny
KX_33 = 2*np.pi*np.arange(mux)/mux 
KY_33 = 2*np.pi*np.arange(muy)/muy
KX_33,KY_33 = np.meshgrid(KX_33,KY_33,indexing='ij')

oracle = mem.cache(PsiOracle)(nx*ny,mux,muy,nx,ny).reshape((mux,muy,nx*ny,mux*nx*muy*ny))
H = mem.cache(HPerp)(N_flatbands,mux,muy,nx,ny)
HCO = cutoff(H,r_cutoff,Nx,Ny)

eig_data_33, e_min_33, e_max_33 = computeEigData(oracle,H,mux,muy,nx,ny)
eig_data_co_33, e_min_co_33, e_max_co_33 = computeEigData(oracle,HCO,mux,muy,nx,ny)

lower_bands = eig_data_co_33[:,:,:N_flatbands]
upper_bands = eig_data_co_33[:,:,N_flatbands:]

Delta_33 = upper_bands.min() - lower_bands.max()
w_33 = lower_bands.max() - lower_bands.min()


print('21: ',f'w = {w_21}', f'Delta = {Delta_21}', f'w/Delta = {w_21/Delta_21}')
print('22: ',f'w = {w_22}', f'Delta = {Delta_22}', f'w/Delta = {w_22/Delta_22}')
print('33: ',f'w = {w_33}', f'Delta = {Delta_33}', f'w/Delta = {w_33/Delta_33}')


norm = colors.Normalize(vmin=min(e_min_21,e_min_co_21,e_min_22,e_min_co_22,e_min_33,e_min_co_33)
                        ,vmax=max(e_max_21,e_max_co_21,e_max_22,e_max_co_22,e_max_33,e_max_co_33))
mappable = cm.ScalarMappable(norm=norm,cmap=cm.coolwarm)
mappable.set_array([])

for d in range(3): 
    axes[0,0].plot_surface(KX_21,KY_21,eig_data_21[:,:,d],cmap=cm.coolwarm,linewidth=0,norm=norm,antialiased=False,)
axes[0,0].set_title(r'$H_{21}$',fontsize=11)
axes[0,0].view_init(elev=15, azim=45)
axes[0,0].tick_params(axis='x', labelbottom=False)
axes[0,0].tick_params(axis='y', labelleft=False)
axes[0,0].tick_params(axis='z', labelleft=False)

for d in range(3): 
    axes[1,0].plot_surface(KX_21,KY_21,eig_data_co_21[:,:,d],cmap=cm.coolwarm,linewidth=0,norm=norm,antialiased=False,)
axes[1,0].set_title(r'$r_\text{cutoff} = $' + f'{3}',fontsize=10,y=-.1)
axes[1,0].view_init(elev=15, azim=45)
axes[1,0].tick_params(axis='x', labelbottom=False)
axes[1,0].tick_params(axis='y', labelleft=False)
axes[1,0].tick_params(axis='z', labelleft=False)

for d in range(4): 
    axes[0,1].plot_surface(KX_22,KY_22,eig_data_22[:,:,d],cmap=cm.coolwarm,linewidth=0,norm=norm,antialiased=False,)
axes[0,1].set_title(r'$H_{22}$',fontsize=11)
axes[0,1].view_init(elev=15, azim=45)
axes[0,1].tick_params(axis='x', labelbottom=False)
axes[0,1].tick_params(axis='y', labelleft=False)
axes[0,1].tick_params(axis='z', labelleft=False)

for d in range(4): 
    axes[1,1].plot_surface(KX_22,KY_22,eig_data_co_22[:,:,d],cmap=cm.coolwarm,linewidth=0,norm=norm,antialiased=False,)
axes[1,1].set_title(r'$r_\text{cutoff} = $' + f'{4}',fontsize=10,y=-.1)
axes[1,1].view_init(elev=15, azim=45)
axes[1,1].tick_params(axis='x', labelbottom=False)
axes[1,1].tick_params(axis='y', labelleft=False)
axes[1,1].tick_params(axis='z', labelleft=False)

for d in range(12): 
    axes[0,2].plot_surface(KX_33,KY_33,eig_data_33[:,:,d],cmap=cm.coolwarm,linewidth=0,norm=norm,antialiased=False,)
axes[0,2].set_title(r'$H_{33}$',fontsize=11)
axes[0,2].view_init(elev=15, azim=45)
axes[0,2].tick_params(axis='x', labelbottom=False)
axes[0,2].tick_params(axis='y', labelleft=False)
axes[0,2].tick_params(axis='z', labelleft=False)

for d in range(12): 
    axes[1,2].plot_surface(KX_33,KY_33,eig_data_co_33[:,:,d],cmap=cm.coolwarm,linewidth=0,norm=norm,antialiased=False,)
axes[1,2].set_title(r'$r_\text{cutoff} = $' + f'{8}',fontsize=10,y=-.1)
axes[1,2].view_init(elev=15, azim=45)
axes[1,2].tick_params(axis='x', labelbottom=False)
axes[1,2].tick_params(axis='y', labelleft=False)
axes[1,2].tick_params(axis='z', labelleft=False)

fig.colorbar(mappable=mappable,ax=axes,location='right',shrink =.9,aspect=15)
 
plt.show()
