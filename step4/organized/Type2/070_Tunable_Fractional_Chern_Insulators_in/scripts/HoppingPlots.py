from LatticePartons import * 

######################################################################################################################################################################
# 2D hopping strength for H21 H22 and H33 for two system sizes
#######################################################################################################################################################################

fig, axs = plt.subplots(2,3,constrained_layout=True,figsize=(3.4, 2.1))

# H21
nx, ny = 2,2
N_flatbands = 2
mux,muy = 7,7
scale_factor = 2
mux_big, muy_big = scale_factor*mux, scale_factor*muy

extent_small = (-int(nx*mux/2),int(nx*mux/2),-int(ny*muy/2),int(ny*muy/2))
extent_big = (-int(nx*mux_big/2),int(nx*mux_big/2),-int(ny*muy_big/2),int(ny*muy_big/2))

H = computeHoppingData(N_flatbands,mux,muy,nx,ny)[1:,1:]
H_big = computeHoppingData(N_flatbands,mux_big,muy_big,nx,ny)[1:,1:]

norm = colors.Normalize(vmin=0,vmax=1)
axs[0,0].imshow(H,cmap='coolwarm',norm=norm,extent=extent_small)
axs[0,0].set_title(r'$H_{21}$')
axs[1,0].imshow(H_big,cmap='coolwarm',norm=norm,extent=extent_big)
axs[0,0].set_yticks([])
axs[1,0].set_yticks([])


# H22
nx, ny = 2,2
N_flatbands = 3
mux,muy = 9,9
scale_factor = 2
mux_big, muy_big = scale_factor*mux, scale_factor*muy

extent_small = (-int(nx*mux/2),int(nx*mux/2),-int(ny*muy/2),int(ny*muy/2))
extent_big = (-int(nx*mux_big/2),int(nx*mux_big/2),-int(ny*muy_big/2),int(ny*muy_big/2))

H = computeHoppingData(N_flatbands,mux,muy,nx,ny)[1:,1:]
H_big = computeHoppingData(N_flatbands,mux_big,muy_big,nx,ny)[1:,1:]

norm = colors.Normalize(vmin=0,vmax=1)
axs[0,1].imshow(H,cmap='coolwarm',norm=norm,extent=extent_small)
axs[0,1].set_title(r'$H_{22}$')
axs[1,1].imshow(H_big,cmap='coolwarm',norm=norm,extent=extent_big)
axs[0,1].set_yticks([])
axs[1,1].set_yticks([])


# H33
nx, ny = 6,2
N_flatbands = 5
mux,muy = 4,12
scale_factor = 2
mux_big, muy_big = scale_factor*mux, scale_factor*muy

extent_small = (-int(nx*mux/2),int(nx*mux/2),-int(ny*muy/2),int(ny*muy/2))
extent_big = (-int(nx*mux_big/2),int(nx*mux_big/2),-int(ny*muy_big/2),int(ny*muy_big/2))

H = computeHoppingData(N_flatbands,mux,muy,nx,ny)[1:,1:]
H_big = computeHoppingData(N_flatbands,mux_big,muy_big,nx,ny)[1:,1:]

norm = colors.Normalize(vmin=0,vmax=1)
axs[0,2].imshow(1.3*H,cmap='coolwarm',norm=norm,extent=extent_small)
axs[0,2].set_title(r'$H_{33}$')
axs[1,2].imshow(1.3*H_big,cmap='coolwarm',norm=norm,extent=extent_big)
axs[1,2].set_xticks([-15,0,15])
axs[0,2].set_yticks([])
axs[1,2].set_yticks([])


norm = colors.Normalize(vmin=0,vmax=1)
mappable = cm.ScalarMappable(norm=norm,cmap=cm.coolwarm)
fig.colorbar(mappable=mappable,ax=axs,location='right',shrink=1,aspect=15,ticks=[0,0.5,1])

plt.show()

#######################################################################################################################################################################
# 3D hopping strength plots for H21 H22 and H33
#######################################################################################################################################################################
fig, axs = plt.subplots(1,3,constrained_layout=True,subplot_kw={"projection": "3d"},figsize=(4,1.4))
norm = colors.Normalize(vmin=0,vmax=1)
mappable = cm.ScalarMappable(norm=norm,cmap=cm.coolwarm)

# H21
nx, ny = 2,2
N_flatbands = 2
mux,muy = 7,7
Nx, Ny = nx*mux, ny*muy

extent = (-int(nx*mux/2),int(nx*mux/2),-int(ny*muy/2),int(ny*muy/2))

H = computeHoppingData(N_flatbands,mux,muy,nx,ny)[1:,1:]
H_face = np.maximum.reduce(
    [H[:-1, :-1],
    H[1:,  :-1],  
    H[:-1, 1:],   
    H[1:,  1:],])
face_rgba = cm.coolwarm(norm(H_face))
Xs, Ys = np.arange(Nx)[1:], np.arange(Ny)[1:]
Xs, Ys = np.meshgrid(Xs,Ys,indexing='ij')

axs[0].set_title(r'$H_{21}$',fontsize=12)
axs[0].plot_surface(Xs,Ys,H,cmap='coolwarm',norm=norm,facecolors=face_rgba)
axs[0].view_init(elev=15, azim=45)
axs[0].set_xticks([0,Nx/2,Nx])
axs[0].invert_xaxis()
axs[0].tick_params(axis='x', pad=-4)
axs[0].tick_params(axis='y', labelleft=False)
axs[0].tick_params(axis='z', labelleft=False)


# H22
nx, ny = 2,2
N_flatbands = 3
mux,muy = 9,9
Nx, Ny = nx*mux, ny*muy

extent = (-int(nx*mux/2),int(nx*mux/2),-int(ny*muy/2),int(ny*muy/2))

H = computeHoppingData(N_flatbands,mux,muy,nx,ny)[1:,1:]
H_face = np.maximum.reduce(
    [H[:-1, :-1],
    H[1:,  :-1],  
    H[:-1, 1:],   
    H[1:,  1:],])
face_rgba = cm.coolwarm(norm(H_face))
Xs, Ys = np.arange(Nx)[1:], np.arange(Ny)[1:]
Xs, Ys = np.meshgrid(Xs,Ys,indexing='ij')

axs[1].set_title(r'$H_{22}$',fontsize=12)
axs[1].plot_surface(Xs,Ys,H,cmap='coolwarm',norm=norm,facecolors=face_rgba)
axs[1].view_init(elev=15, azim=45)
axs[1].set_xticks([0,Nx/2,Nx])
axs[1].invert_xaxis()
axs[1].tick_params(axis='x', pad=-4)
axs[1].tick_params(axis='y', labelleft=False)
axs[1].tick_params(axis='z', labelleft=False)

# H33
nx, ny = 6,2
N_flatbands = 5
mux,muy = 4,12
Nx, Ny = nx*mux, ny*muy

extent = (-int(nx*mux/2),int(nx*mux/2),-int(ny*muy/2),int(ny*muy/2))

H = computeHoppingData(N_flatbands,mux,muy,nx,ny)[1:,1:]
H_face = np.maximum.reduce(
    [H[:-1, :-1],
    H[1:,  :-1],  
    H[:-1, 1:],   
    H[1:,  1:],])
face_rgba = cm.coolwarm(norm(H_face))
Xs, Ys = np.arange(Nx)[1:], np.arange(Ny)[1:]
Xs, Ys = np.meshgrid(Xs,Ys,indexing='ij')

axs[2].set_title(r'$H_{33}$',fontsize=12)
axs[2].plot_surface(Xs,Ys,H,cmap='coolwarm',norm=norm,facecolors=face_rgba)
axs[2].view_init(elev=15, azim=45)
axs[2].set_xticks([0,Nx/2,Nx])
axs[2].invert_xaxis()
axs[2].tick_params(axis='x', pad=-4)
axs[2].tick_params(axis='y', labelleft=False)
axs[2].tick_params(axis='z', labelleft=False)

fig.colorbar(mappable=mappable,ax=axs,location='right',shrink=1,aspect=10,ticks=[0,0.5,1])

plt.show()


