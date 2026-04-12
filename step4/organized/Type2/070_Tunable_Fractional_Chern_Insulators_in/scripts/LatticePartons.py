import numpy as np
import math 
import time 
import cmath 
import itertools
import scipy.special as sp
import scipy.sparse as spr
import scipy.linalg as spl 
from joblib import Parallel, delayed
from joblib import Memory 
from multiprocessing import shared_memory
from tqdm import tqdm
import os
import matplotlib.pyplot as plt 
from matplotlib import cm,colors


i = complex(0,1)

os.makedirs('memory',exist_ok=True)
mem = Memory(None,verbose = 0)


def grahamSchmidt(vecs):
    us = []
    def proj(u,v):
        return (np.vdot(v,u)/np.vdot(u,u))*np.array(u) 
    for v in vecs:
        us.append(np.array(v)-sum(proj(u,v) for u in us)) 
    out = np.array([u/np.linalg.norm(u) for u in us])
    return out 

def PositionToIndex(nx,ny,mux,muy,x,y):
    Nx, Ny = nx*mux, ny*muy
    x %= Nx; y %= Ny
    return x*Ny + y

def IndexToPosition(nx,ny,mux,muy,ind):
    Ny = ny*muy
    y = ind % Ny
    x = (ind-y) // Ny
    return (x,y)

def LMax(tau,Ny,factor):
    t = np.imag(tau)
    return int(np.abs(Ny/t + np.sqrt((Ny/t)**2+factor))) 

def theta(lMax,nx,ny,a,b,d=0):
    tau, phi = i*ny/nx, 1/(nx*ny)
    def THETA(x,y):
        z = (x+i*y)/nx
        return sum((i*2*np.pi*(l+a))**d*(cmath.exp(i*np.pi*(l+a)**2*tau+i*2*np.pi*(l+a)*(z+b)-np.pi*phi*y**2)) for l in range(-lMax,lMax+1))
    return THETA

def Psi(lMax,nx,ny,a,b,d=0):
    phi = 1/(nx*ny)
    def PSI(x,y):
        out = 0
        prefactor = i*np.sqrt(np.pi*phi*nx**2/2) 
        for p in range(d+1):
            herm_poly_coeffs = sp.hermite(p).coeffs
            herm = np.polyval(herm_poly_coeffs,np.sqrt(2*np.pi*phi)*y)
            out += math.comb(d,p)*prefactor**p*herm*theta(lMax,nx,ny,a,b,d-p)(x,y) 
        return (1/nx**d)*out 
    return PSI 

def PsiUCOracle(N_flatbands,mux,muy,nx,ny):
    tau = i*ny/nx
    lMax = LMax(tau,ny*muy,5)
    out = np.zeros((mux,muy,N_flatbands,nx,ny),dtype='complex')
    points = [(alpha,beta,d) for alpha in range(mux) for beta in range(muy) for d in range(N_flatbands)]
    for alpha,beta,d in tqdm(points,desc='computing PsiUCOrc'):
        a,b = -alpha/mux, beta/muy
        psi = Psi(lMax,nx,ny,a,b,d)
        for x in range(nx):
            for y in range(ny):
                out[alpha,beta,d,x,y] = psi(x,y+np.pi/(2*ny))
    return out

def HPerp(N_flatbands,mux,muy,nx,ny):
    Nx,Ny = nx*mux, ny*muy
    phi = 1/(nx*ny)
    q = nx*ny-N_flatbands
    psis_uc = PsiUCOracle(nx*ny,mux,muy,nx,ny).reshape((mux,muy,nx*ny,nx*ny))
    valence = psis_uc[:,:,:N_flatbands,:]
    H = np.zeros((Nx*Ny,Nx*Ny),dtype='complex')
    k_points = [(alpha,beta) for alpha in range(mux) for beta in range(muy)]
    for alpha,beta in tqdm(k_points,desc='computing HPerp'):
        a, b = -alpha/mux, beta/muy
        with np.errstate(divide="ignore", invalid="ignore"):
            Psi = np.transpose(valence[alpha,beta])
            K_ab = np.abs(np.linalg.det((Psi.conj().T)@Psi))
        parallel_basis_ab,_ = np.linalg.qr(valence[alpha,beta].T) 
        parallel_projector_ab = sum(np.outer(parallel_basis_ab[:,j],np.conj(parallel_basis_ab[:,j])) for j in range(N_flatbands))
        perp_projector_ab = np.eye(nx*ny) - parallel_projector_ab
        perp_vecs = perp_projector_ab@np.transpose(psis_uc[alpha,beta])
        perp_basis_ab_uc,_,_ = spl.qr(perp_vecs,pivoting=True)
        perp_basis_ab_uc = perp_basis_ab_uc[:,:q]
        perp_basis_ab = np.zeros((Nx,Ny,q),dtype='complex')
        for r in range(nx*ny):
            x = r // ny
            y = r % ny
            v = perp_basis_ab_uc[r,:]
            for A in range(mux):
                for B in range(muy):
                    exp1 = cmath.exp(i*2*np.pi*(a*A-b*B))
                    exp2 = cmath.exp(-i*2*np.pi*phi*ny*B*x)
                    perp_basis_ab[x+A*nx,y+B*ny,:] = exp1*exp2*v/np.sqrt(mux*muy)
        perp_basis_ab = perp_basis_ab.reshape((Nx*Ny,q))
        H += sum(K_ab*np.outer(perp_basis_ab[:,j],np.conjugate(perp_basis_ab[:,j])) for j in range(q))
    return H/(np.abs(H).max())

def PsiOracle(N_flatbands,mux,muy,nx,ny):
    phi = 1/(nx*ny)
    Nx,Ny = nx*mux, ny*muy
    uc_orc = mem.cache(PsiUCOracle)(N_flatbands,mux,muy,nx,ny)
    out = np.zeros((mux,muy,N_flatbands,Nx,Ny),dtype='complex')
    for alpha in range(mux):
        a = -alpha/mux
        for beta in range(muy):
            b = beta/muy
            for d in range(N_flatbands):
                for x0 in range(nx):
                    for y0 in range(ny):
                        v = uc_orc[alpha,beta,d,x0,y0]
                        for A in range(mux):
                            for B in range(muy):
                                exp1 = cmath.exp(i*2*np.pi*(a*A-b*B))
                                exp2 = cmath.exp(-i*2*np.pi*phi*ny*B*x0)
                                out[alpha,beta,d,x0+A*nx,y0+B*ny] = exp1*exp2*v
    return out

def PerpUCOracle(alphas,N_flatbands,mux,muy,nx,ny):
    q = nx*ny - N_flatbands
    out = np.zeros((mux,muy,len(alphas),nx*ny),dtype='complex')
    psi_uc_oracle = mem.cache(PsiUCOracle)(N_flatbands,mux,muy,nx,ny)
    psi_uc_oracle = psi_uc_oracle.reshape((mux,muy,N_flatbands,nx*ny)) 
    for alpha_ind, alpha in enumerate(alphas):
        alpha_sign = -1 if (sum(alpha)+q)%2 else 1
        mask = np.ones(nx*ny,dtype='bool')
        mask[list(alpha)] = 0
        positions = np.flatnonzero(mask)
        for r_ind in range(len(positions)):
            r = positions[r_ind] 
            remaining_positions = np.delete(positions,r_ind) 
            sign = -1 if sum([a < r for a in remaining_positions])%2 else 1
            for a in range(mux):
                for b in range(muy):
                    psi_small = np.array([[np.conjugate(psi_uc_oracle[a,b,d,R]) for d in range(N_flatbands)] for R in remaining_positions])
                    with np.errstate(divide="ignore", invalid="ignore"):
                        psi_small_det = np.linalg.det(psi_small)
                    out[a,b,alpha_ind,r] = (1/N_flatbands)*alpha_sign*sign*psi_small_det
    return out.reshape((mux,muy,len(alphas),nx,ny))  

def PerpOracle(alphas,N_flatbands,mux,muy,nx,ny):
    phi = 1/(nx*ny)
    Nx,Ny = mux*nx, muy*ny
    perp_uc_oracle = mem.cache(PerpUCOracle)(alphas,N_flatbands,mux,muy,nx,ny)
    out = np.zeros((mux,muy,len(alphas),Nx,Ny),dtype='complex')
    for alpha in range(mux):
        a = -alpha/mux
        for beta in range(muy):
            b = beta/muy
            for alpha_ind in range(len(alphas)):
                for x0 in range(nx):
                    for y0 in range(ny):
                        v = perp_uc_oracle[alpha,beta,alpha_ind,x0,y0]
                        for A in range(mux):
                            for B in range(muy):
                                exp1 = cmath.exp(i*2*np.pi*(a*A-b*B))
                                exp2 = cmath.exp(-i*2*np.pi*phi*ny*B*x0)
                                out[alpha,beta,alpha_ind,x0+A*nx,y0+B*ny] = exp1*exp2*v
    return out.reshape((mux,muy,len(alphas),Nx*Ny))

def HPerpGeneral(N_flatbands,mux,muy,nx,ny,n_jobs=1):
    Nx,Ny = nx*mux, ny*muy
    alphas = list(itertools.combinations(range(nx*ny),nx*ny-N_flatbands-1))
    L_alpha = len(alphas)
    perp_oracle = mem.cache(PerpOracle)(alphas,N_flatbands,mux,muy,nx,ny)
    points = [(a,b,ind) for a in range(mux) for b in range(muy) for ind in range(L_alpha)]
    def H_block(a,b,ind):
        data = np.zeros((Nx*Ny,Nx*Ny),dtype='complex')
        for R in range(Nx*Ny):
            data[R,R] = perp_oracle[a,b,ind,R]*np.conjugate(perp_oracle[a,b,ind,R])/2
            for Rp in range(R+1,Nx*Ny):
                data[R,Rp] = perp_oracle[a,b,ind,R]*np.conjugate(perp_oracle[a,b,ind,Rp])
        return data 
    blocks = Parallel(n_jobs=n_jobs,backend='loky')(delayed(H_block)(a,b,ind) for (a,b,ind) in tqdm(points,desc='computing HPerp')) 
    H = sum(blocks)
    H = H + np.conj(H.T)
    return H/(np.abs(H).max())

def TorusDist(Nx,Ny):
    def d(R,Rp):
        y, yp = R%Ny, Rp%Ny
        x, xp = R//Ny, Rp//Ny
        dx, dy = min((x-xp)%Nx,(xp-x)%Nx), min((y-yp)%Ny,(yp-y)%Ny)
        return np.sqrt(dx**2+dy**2)
    return d 

def cutoff(H,r,Nx,Ny):
    d = TorusDist(Nx,Ny)
    out = H.copy()
    for R1 in range(Nx*Ny):
        for R2 in range(Nx*Ny):
            if d(R1,R2) > r: 
                out[R1,R2] = 0
    return out

def plotBandStructure(H,mux,muy,nx,ny):
    oracle = mem.cache(PsiOracle)(nx*ny,mux,muy,nx,ny).reshape((mux,muy,nx*ny,mux*nx*muy*ny))
    eig_data = np.zeros((mux,muy,nx*ny))
    for alpha in range(mux):
        for beta in range(muy):
            basis, _ = np.linalg.qr(oracle[alpha,beta].T,mode='reduced')
            Hab = (basis.conj().T)@H@basis
            eigs,_ = np.linalg.eigh(Hab)
            eig_data[alpha,beta] = eigs
    e_min, e_max = np.min(eig_data), np.max(eig_data) 
    eig_data = eig_data - e_min
    KX = 2*np.pi*np.arange(mux)/mux
    KY = 2*np.pi*np.arange(muy)/muy
    KX,KY = np.meshgrid(KX,KY,indexing='ij')
    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    norm = colors.Normalize(vmin=e_min,vmax=e_max)
    for d in range(nx*ny): 
        ax.plot_surface(KX,KY,eig_data[:,:,d],cmap=cm.coolwarm,linewidth=0,norm=norm,antialiased=False)
    mappable = cm.ScalarMappable(norm=norm,cmap=cm.coolwarm)
    mappable.set_array([])
    fig.colorbar(mappable=mappable,ax=ax)

def IndexFromState(L,N_electrons,state,order='lex'):
    assert order in ('lex','colex')
    if order == 'lex':
        r = 0
        prev = -1
        j = 0
        for pos in range(L):
            if state & (1 << pos):
                for t in range(prev + 1, pos):
                    r += math.comb(L-1-t,N_electrons-1-j)
                prev = pos
                j += 1
                if j == N_electrons:
                    break
        return r
    if order == 'colex':
        count = 0
        particles_seen = 0
        for pos in range(L):
            if state & (1 << pos):
                particles_seen += 1
                count += math.comb(pos, particles_seen)
                if particles_seen == N_electrons:
                    break
        return count

def NParticleHardCoreStates(L,N_electrons,return_dict = False):
    #uses a binary representation of the states where a particle in site k means the coeffcient of 2^k is 1 etc. 
    if return_dict:
        state_dict = dict()
        states = np.zeros(int(mem.cache(sp.binom)(L,N_electrons)),dtype='int')
        for ind, comb in enumerate(itertools.combinations(range(L), N_electrons)):
            state = sum(1 << i for i in comb)
            states[ind] = state
            state_dict.update({state : ind})
        return states, state_dict
    else:
        return [sum(1 << i for i in comb) for comb in itertools.combinations(range(L), N_electrons)]


def TranslateManyBodyState(state,A,B,nx,ny,mux,muy):
    L = int(state).bit_length()
    Nx , Ny = nx*mux, ny*muy
    gauge_phase_positions = 0
    new_state = 0
    for k in range(L):
        if state & (1<<k):
            x,y = IndexToPosition(nx,ny,mux,muy,k)
            x_trans, y_trans = (x+A*nx)%Nx, (y+B*ny)%Ny
            winding = (y + B*ny) // Ny
            if winding: #We make the identification c^\dagger_{R+Ny} \equiv e^{-i 2 \pi \phi x Ny} c^\dagger_R to handle 
                    #gauge transformations that cross periodic boundary
                gauge_phase_positions += -muy*x_trans*winding 
            gauge_phase_positions += B*x_trans
            new_state += 1<<PositionToIndex(nx,ny,mux,muy,x_trans,y_trans)
    return new_state, gauge_phase_positions

def MTGTranslates(state,nx,ny,mux,muy):
    return [TranslateManyBodyState(state,A,B,nx,ny,mux,muy) for A in range(mux) for B in range(muy)]

def MTGProjector(Kx_ind,Ky_ind,**params):
    filling_fraction,mux,muy,nx,ny = (params[x] for x in ('filling_fraction','mux','muy','nx','ny'))
    phi = 1/(nx*ny)
    Nx, Ny = mux*nx, muy*ny
    N_electrons = int(filling_fraction*mux*muy)
    L = Nx*Ny
    Kx, Ky = 2*np.pi*Kx_ind/mux, 2*np.pi*Ky_ind/muy
    hard_core_states, hard_core_dict = mem.cache(NParticleHardCoreStates)(L,N_electrons,return_dict=True)
    D = len(hard_core_states)
    visited = np.zeros(D,dtype='bool')
    basis_state_number = 0
    rows, cols, vals = [], [], []
    for state in hard_core_states:
        if not visited[hard_core_dict[state]]:
            row, col, val = [], [], [] 
            translates = MTGTranslates(state,nx,ny,mux,muy)
            state_coeffs = dict()
            for A in range(mux):
                for B in range(muy):
                    translated_state, gauge_phase_positions = translates[A*muy+B]
                    translated_state_idx = hard_core_dict[translated_state]
                    visited[translated_state_idx] = 1
                    mech_phase_arg = Kx*A - Ky*B
                    gauge_phase_arg = 2*np.pi*phi*ny*gauge_phase_positions
                    state_coeffs[translated_state_idx] = state_coeffs.get(translated_state_idx,0) + cmath.exp(i*(mech_phase_arg+gauge_phase_arg))
            for tsi, coeff in state_coeffs.items():
                    col.append(tsi); val.append(coeff)
            norm = np.linalg.norm(val)
            if norm >= 1e-10:
                row = [basis_state_number]*len(col)
                rows += row; cols += col; vals += [v/norm for v in val] 
                basis_state_number += 1
    dk = basis_state_number
    Udagger = spr.coo_matrix((vals, (rows, cols)), shape=(dk,D)).tocsr()
    Udagger.sum_duplicates()
    Udagger.eliminate_zeros()
    return Udagger

def ManyBodyHPerp(**params):
    N_flatbands,filling_fraction,mux,muy,nx,ny,n_jobs, = (params[x] for x in ('N_flatbands','filling_fraction','mux','muy','nx','ny','n_jobs'))
    tol = params.get('tol',1e-6)
    r_cutoff = params.get('r_cutoff',None)
    Nx,Ny = nx*mux, ny*muy
    N_electrons = int(filling_fraction*mux*muy)
    L = Nx*Ny
    H_One_Body = mem.cache(HPerp)(N_flatbands,mux,muy,nx,ny)
    if r_cutoff is not None:
        H_One_Body = cutoff(H_One_Body,r_cutoff,Nx,Ny)
    states = mem.cache(NParticleHardCoreStates)(L,N_electrons-1) #Since H is one body it only connects states which differ by the position of at most one particle
    #therefore we can compute matrix elements of H efficiently by computing the states with N-1 particles, and putting the new particles in one at a time 
    N_states = math.comb(L,N_electrons-1)
    per_state_nnz = (L-N_electrons+1)**2
    shm_row = shared_memory.SharedMemory(create=True,size=per_state_nnz*N_states*np.dtype(np.int64).itemsize)
    shm_col = shared_memory.SharedMemory(create=True,size=per_state_nnz*N_states*np.dtype(np.int64).itemsize)
    shm_val = shared_memory.SharedMemory(create=True,size=per_state_nnz*N_states*np.dtype(np.complex128).itemsize)
    shm_count = shared_memory.SharedMemory(create=True,size=N_states * np.dtype(np.int64).itemsize)
    row = np.ndarray((per_state_nnz*N_states),dtype=np.int64,buffer=shm_row.buf)
    col = np.ndarray((per_state_nnz*N_states),dtype=np.int64,buffer=shm_col.buf)
    val = np.ndarray((per_state_nnz*N_states),dtype=np.complex128,buffer=shm_val.buf)
    count = np.ndarray((N_states,), dtype=np.int64, buffer=shm_count.buf)
    def FillBlock(number_of_states,state,state_index,L,N_electrons,H_One_Body,mem_names,per_state_nnz,tol):
        shm_row = shared_memory.SharedMemory(name=mem_names[0])
        shm_col = shared_memory.SharedMemory(name=mem_names[1])
        shm_val = shared_memory.SharedMemory(name=mem_names[2])
        shm_count = shared_memory.SharedMemory(name=mem_names[3])
        row = np.ndarray((number_of_states*per_state_nnz),dtype=np.int64,buffer=shm_row.buf)
        col = np.ndarray((number_of_states*per_state_nnz),dtype=np.int64,buffer=shm_col.buf)
        val = np.ndarray((number_of_states*per_state_nnz),dtype=np.complex128,buffer=shm_val.buf)
        count = np.ndarray((number_of_states,), dtype=np.int64, buffer=shm_count.buf)
        try: 
            occupied_sites = np.fromiter(((state >> x)&1 for x in range(L)),dtype=np.uint8,count=L)
            empty_sites = np.flatnonzero(occupied_sites==0) 
            offset = state_index*per_state_nnz
            ind = offset
            for R_position, R in enumerate(empty_sites):
                R_state = state | (1<<R)
                R_state_index = IndexFromState(L,N_electrons,R_state)
                h = H_One_Body[R,R]
                if np.abs(h) > tol:
                    row[ind] = R_state_index; col[ind] = R_state_index; val[ind] = H_One_Body[R,R]; ind += 1
                for Rp in empty_sites[R_position+1:]:
                    h = H_One_Body[R,Rp]
                    if np.abs(h) > tol:
                        Rp_state = state | (1<<Rp)
                        Rp_state_index = IndexFromState(L,N_electrons,Rp_state)    
                        row[ind] = R_state_index; col[ind] = Rp_state_index; val[ind] = h; ind+=1
                        row[ind] = Rp_state_index; col[ind] = R_state_index; val[ind] = np.conj(h); ind+=1 
            count[state_index] = ind-offset
        finally:
            shm_row.close(); shm_col.close(); shm_val.close(); shm_count.close() 
    try:
        mem_names = (shm_row.name,shm_col.name,shm_val.name,shm_count.name)
        Parallel(n_jobs=n_jobs,backend='loky')(delayed(FillBlock)(N_states,state,state_index,L,N_electrons,H_One_Body,mem_names,per_state_nnz,tol) 
                                               for state_index,state in tqdm(enumerate(states),total=N_states,desc='Computing HMB'))
        D = math.comb(L, N_electrons)
        counts = count.copy()
        total_nnz = int(count.sum())
        keep = np.empty(total_nnz,dtype=np.int64)
        pos = 0
        for state_index, c in enumerate(counts):
            off = state_index*per_state_nnz
            keep[pos:pos+c] = np.arange(off,off+c)
            pos += c
        H = spr.coo_matrix((val[keep], (row[keep], col[keep])), shape=(D, D)).tocsr()
        return H
    finally:
        shm_row.close(); shm_row.unlink(); 
        shm_col.close(); shm_col.unlink(); 
        shm_val.close(); shm_val.unlink(); 
        shm_count.close(); shm_count.unlink()

def DiagonalizeHMB(H=None,number_eigvals=10,method='Lanczos',momentum_sector_projection=True,tol=1e-12,maxiter=None,v0=None,**params):
    if H is None:
        H = mem.cache(ManyBodyHPerp)(**params)
    if momentum_sector_projection:
        mux,muy,n_jobs = (params[x] for x in ('mux','muy','n_jobs'))
        K_points = [(A,B) for A in range(mux) for B in range(muy)]
        def DiagHk(A,B):
            Udagger = mem.cache(MTGProjector)(A,B,**params)
            U = Udagger.getH()
            if method == 'Dense':
                Hk = (Udagger@H@U).toarray()
                vals,_ = np.linalg.eigh(Hk)
                return (A,B), vals  
            if method == 'Lanczos':
                dk = Udagger.shape[0]
                if number_eigvals == -1:
                    n_eigvals_k = dk
                else:
                    n_eigvals_k = min(dk,number_eigvals)
                Hk = Udagger@H@U
                print(f'Hk dim and nnz for {(A,B)} sector: {(Hk.shape[0]),Hk.nnz} ')
                t0 = time.perf_counter()
                vals = spr.linalg.eigsh(Hk,k=n_eigvals_k,sigma=-1e-5,which='LM',tol=tol,v0=v0,maxiter=maxiter,return_eigenvectors=False) 
                tf = time.perf_counter()
                print(f'diagonalization time for {(A,B)} sector: {tf-t0}')
            return (A,B), np.sort(vals)
        eig_data = Parallel(n_jobs=n_jobs,prefer='threads')(delayed(DiagHk)(A,B) for (A,B) in tqdm(K_points,desc='Diagonalizing HMB')) 
        return dict(eig_data)
    else:
        if method == 'Dense':
            vals,_ = np.linalg.eigh(H.toarray())
        if method == 'Lanczos':
            if number_eigvals == -1:
                number_eigvals = H.shape[0]
            vals = spr.linalg.eigsh(H,k=number_eigvals,sigma=-1e-5,which='LM',tol=tol,v0=v0,maxiter=maxiter,return_eigenvectors=False)
        return np.sort(vals)

def plotHoppingStrength(N_flatbands,mux,muy,nx,ny):
    Nx,Ny = mux*nx, muy*ny
    xs = np.arange(0,Nx)
    ys = np.arange(0,Ny)
    Y,X = np.meshgrid(ys,xs)
    H = np.abs(mem.cache(HPerp)(N_flatbands,mux,muy,nx,ny))
    hoppingData = np.zeros((Nx,Ny))
    for R in range(Nx*Ny):
        y = R%Ny
        x = int((R-y)/Ny)
        hoppingData[x-int(Nx/2)][y-int(Ny/2)] = H[0,R]
    hoppingData = hoppingData/(np.max(hoppingData))
    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    surf = ax.plot_surface(X,Y,hoppingData,cmap=cm.coolwarm,
                       linewidth=0, antialiased=False)
    ax.set_xlabel('$x$', fontsize=12)
    ax.set_ylabel('$y$', fontsize=12)
    ax.set_zticks([])
    ax.set_title('Hopping strength')
    plt.colorbar(surf,shrink=0.5,aspect=5,label="$\\langle 0|H^\\perp|R\\rangle $")
    plt.show()

def computeHoppingData(N_flatbands,mux,muy,nx,ny):
    Nx,Ny = nx*mux,ny*muy
    xs = np.arange(0,Nx)
    ys = np.arange(0,Ny)
    xs,ys = np.meshgrid(xs,ys)
    H = np.abs(mem.cache(HPerp)(N_flatbands,mux,muy,nx,ny))
    hoppingData = np.zeros((Nx,Ny))
    for R in range(Nx*Ny):
        y = R%Ny
        x = int((R-y)/Ny)           
        hoppingData[x-int(Nx/2)][y-int(Ny/2)] = np.abs(H[0,R])
    hoppingData = hoppingData/(np.max(hoppingData))
    return hoppingData

def HopData(H,Nx,Ny):
    xs = np.arange(0,Nx)
    ys = np.arange(0,Ny)
    xs,ys = np.meshgrid(xs,ys)
    hoppingData = np.zeros((Nx,Ny))
    for R in range(Nx*Ny):
        y = R%Ny
        x = int((R-y)/Ny)           
        hoppingData[x-int(Nx/2)][y-int(Ny/2)] = np.abs(H[0,R])
    hoppingData = hoppingData/(np.max(hoppingData))
    return hoppingData

def plotHoppingMatrices(N_flatbands,mux,muy,nx,ny,n_jobs=1):
    Nx,Ny = nx*mux,ny*muy
    xs = np.arange(0,Nx)
    ys = np.arange(0,Ny)
    xs,ys = np.meshgrid(xs,ys)
    H = np.abs(mem.cache(HPerp)(N_flatbands,mux,muy,nx,ny,n_jobs))
    hoppingData = np.zeros((Nx,Ny))
    for R in range(Nx*Ny):
        y = R%Ny
        x = int((R-y)/Ny)           
        hoppingData[x-int(Nx/2)][y-int(Ny/2)] = np.abs(H[0,R])
    hoppingData = hoppingData/(np.max(hoppingData))
    fig, ax = plt.subplots()
    heatmap = ax.imshow(hoppingData[1:,1:],cmap='coolwarm',interpolation='none')
    colorbar = plt.colorbar(heatmap)
    colorbar.ax.tick_params(labelsize=14)
    colorbar.set_label(r'$t_{R}$',fontsize=20) 
    ticks = np.arange(0,Nx,2)
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xlabel(r'$R_x$',fontsize = 20)
    ax.set_ylabel(r'$R_y$',fontsize = 20)
    ax.tick_params(axis='both', labelsize=14)
    ax.invert_yaxis()
    plt.title(r'$H_{22}$',fontsize = 25)
    plt.tight_layout()
    plt.plot()

def ComputeGap(spec,return_gap_ind=False):
    gap = ind = gap_ind = 0
    for ind in range(len(spec)-1):
        delta = spec[ind+1] - spec[ind]
        if delta > 1e-12 and delta > gap:
            gap = delta
            gap_ind = ind
    if return_gap_ind:
        return gap,gap_ind
    else: 
        return gap

def FindGap(spec):
    deltas = [spec[i+1] - spec[i] for i in range(len(spec)-1)]
    return max(deltas)
    
def CutoffGaps(Rs,H,Nx,Ny):
    out = np.zeros_like(Rs)
    for r in tqdm(Rs,desc='computing cutoff gaps'):
        H_CO = cutoff(H,r,Nx,Ny)
        eigs,_ = np.linalg.eigh(H_CO) 
        out[r] = ComputeGap(eigs)
    return out

def HCODist(H,r,Nx,Ny):
    HCO = cutoff(H,r,Nx,Ny)
    return np.linalg.norm(H-HCO)/np.linalg.norm(H)
