import kwant
import numpy as np
from numpy import cos, sin, pi, exp, sqrt, sinh, log
import scipy.linalg as linalg

import scipy.sparse.linalg as sla
import sys

import matplotlib.pyplot as plt


def Berry_curvature(hamiltonian, kx0, kx1, ky0, ky1, Nk=51, n0=0, fill=1, return_grid=False):
    ''' computes the Berry curvature F12 of a 2D system on a square grid.
        The endpoints of the grid (top and right) are excluded.
        
        The larger interval max([kx0,kx1],[ky0,ky1]) is divided into Nk segements of 
        length dk. The shorter interval of length K is divided into int(K/dk)
        segments.
        
        The Chern number can be obtained by summing F12/2*pi over the entire BZ.
    
        hamiltonian: function that returns the Hamiltonian matrix
        Nk: maximum number of grid points along x or y
        kx0,kx1,ky0,ky1: limits of the rectangular kspace grid.
        n0: first filled state (lowest state has n0=0)
        fill: number of filled states filling (0 < fill <= dim)
        return_grid: if True, the grid point arrays for kx and ky are returned
        
        returns: F12, (optional: kxs, kys)
        
        [based on Fukui, Hatsugai, Suzuki, J. Phys. Soc. Jpn. 74, 1674 (2005)]
    '''
    
    dim = np.shape(hamiltonian(0, 0))[0]
    
    if abs(kx1-kx0) > abs(ky1-ky0):
        Nkx = Nk
        x0, step = np.linspace(kx0, kx1, Nkx+1, endpoint=True, retstep=True)
        Nky = int(abs(ky1-ky0)//step)
        y0 = np.array([(ky0 + i*step) for i in range(Nky+1)])
    else:
        Nky = Nk
        y0, step = np.linspace(ky0, ky1, Nky+1, endpoint=True, retstep=True)
        Nkx = int(abs(kx1-kx0)//step)
        x0 = np.array([(kx0 + i*step) for i in range(Nkx+1)])
        
    xlist = list(x0)
    ylist = list(y0)   
    xlist.append(x0[-1]+step)
    ylist.append(y0[-1]+step)
    x = np.array(xlist)
    y = np.array(ylist)

    evecs = np.zeros((Nkx+2,Nky+2,dim,dim),dtype=complex)
    U1 = np.zeros((Nkx+1,Nky+1),dtype=complex)
    U2 = np.zeros((Nkx+1,Nky+1),dtype=complex)
    F12 = np.zeros((Nkx,Nky),dtype=complex)

    U1temp = np.zeros((fill,fill),dtype=complex)
    U2temp = np.zeros((fill,fill),dtype=complex)

    # compute eigenstates of the systems on the grid
    for i in range(Nkx+2):
        print("\rCompute eigenstates: {:3d}/100".format(int((i+1)/(Nkx+2)*100)), end='')
        for k in range(Nky+2):
            ham = hamiltonian(x[i],y[k])
            evs, evecs[i,k,:,:] = linalg.eigh(ham,eigvals_only=False)

    print()
    # compute U(n) link variable on the grid
    for i in range(Nkx+1):
        print("\rCompute link variables: {:3d}/100".format(int((i+1)/(Nkx+1)*100)), end='')
        for k in range(Nky+1):
            for l in range(fill):
                for m in range(fill):
                    U1temp[l,m] = np.dot(np.conjugate(evecs[i,k,:,n0+l]),evecs[i+1,k,:,n0+m])
                    U2temp[l,m] = np.dot(np.conjugate(evecs[i,k,:,n0+l]),evecs[i,k+1,:,n0+m])
            temp1 = linalg.det(U1temp,overwrite_a=True)
            temp2 = linalg.det(U2temp,overwrite_a=True)
            U1[i,k] = temp1/np.abs(temp1)
            U2[i,k] = temp2/np.abs(temp2)

    print()
    # compute a lattice field strength on the grid
    for i in range(Nkx):
        print("\rCompute Berry curvature: {:3d}/100".format(int((i+1)/(Nkx)*100)), end='')
        for k in range(Nky):
            F12[i,k] = log(U1[i,k]*U2[i+1,k]/U1[i,k+1]/U2[i,k])
                
    # return Berry curvature
    if return_grid:
        return F12.imag, x0, y0
    else:
        return F12.imag

def quantum_geometric_tensor(hamiltonian, kx0, kx1, ky0, ky1, Nk=51, n0=0, fill=1, return_grid=False):
    ''' computes the quantum geometric tensor Gij of a 2D system on a square grid.
        The endpoints of the grid (top and right) are excluded.
        
        The larger interval max([kx0,kx1],[ky0,ky1]) is divided into Nk segements of 
        length dk. The shorter interval of length K is divided into int(K/dk)
        segments.
        
        The Berry curvature is F12 = 2*Im(Gij[0,1]).
        The Fubini-Study metric is gij = Re(Gij).             
    
        hamiltonian: function that returns the Hamiltonian matrix
        Nk: maximum number of grid points along x or y
        kx0,kx1,ky0,ky1: limits of the rectangular kspace grid.
        n0: first filled state (lowest state has n0=0)
        fill: number of filled states filling (0 < fill <= dim)
        return_grid: if True, the grid point arrays for kx and ky are returned
        
        returns: Gij, evals, (optional: kxs, kys)
    '''
    dim = np.shape(hamiltonian(0, 0))[0]
    
    # ensure that the unit plaquette is a square
    if abs(kx1-kx0) > abs(ky1-ky0):
        Nkx = Nk
        x, step = np.linspace(kx0, kx1, Nkx+1, endpoint=True, retstep=True)
        Nky = int(abs(ky1-ky0)//step)
        y = np.array([(ky0 + i*step) for i in range(Nky+1)])
    elif abs(kx1-kx0) == abs(ky1-ky0):
        Nkx = Nk
        Nky = Nk
        x = np.linspace(kx0, kx1, Nkx+1, endpoint=True)
        y = np.linspace(ky0, ky1, Nky+1, endpoint=True)
    else:
        Nky = Nk
        y, step = np.linspace(ky0, ky1, Nky+1, endpoint=True, retstep=True)
        Nkx = int(abs(kx1-kx0)//step)
        x = np.array([(kx0 + i*step) for i in range(Nkx+1)])

    evecs = np.zeros((Nkx+1,Nky+1,dim,dim),dtype=complex)
    evals = np.zeros((Nkx+1,Nky+1,dim))
    V1 = np.zeros((Nkx,Nky),dtype=complex)
    V2 = np.zeros((Nkx,Nky),dtype=complex)
    V12 = np.zeros((Nkx,Nky),dtype=complex)
    G = np.zeros((2,2,Nkx,Nky),dtype=complex)

    V1temp = np.zeros((fill,fill),dtype=complex)
    V2temp = np.zeros((fill,fill),dtype=complex)
    V12temp = np.zeros((fill,fill),dtype=complex)
    
    # compute eigenstates of the systems on the grid
    for i in range(Nkx+1):
        print("\rCompute eigenstates: {:3d}/100".format(int((i+1)/(Nkx+1)*100)), end='')
        for k in range(Nky+1):
            ham = hamiltonian(x[i],y[k])
            evals[i,k,:], evecs[i,k,:,:] = linalg.eigh(ham)
    
    print()
    # compute link variable on the grid
    for i in range(Nkx):
        print("\rCompute link variables: {:3d}/100".format(int((i+1)/(Nkx)*100)), end='')
        for k in range(Nky):
            for l in range(fill):
                for m in range(fill):
                    V1temp[l,m] = np.dot(np.conjugate(evecs[i,k,:,n0+l]),evecs[i+1,k,:,n0+m])
                    V2temp[l,m] = np.dot(np.conjugate(evecs[i,k,:,n0+l]),evecs[i,k+1,:,n0+m])
                    V12temp[l,m] = np.dot(np.conjugate(evecs[i+1,k,:,n0+l]),evecs[i,k+1,:,n0+m])                    
            V1[i,k] = linalg.det(V1temp, overwrite_a=True)
            V2[i,k] = linalg.det(V2temp, overwrite_a=True)
            V12[i,k] = linalg.det(V12temp, overwrite_a=True)
            
    print()
    # compute a lattice field strength on the grid
    for i in range(Nkx):
        print("\rCompute quantum geometric tensor: {:3d}/100".format(int((i+1)/(Nkx)*100)), end='')
        for k in range(Nky):
            G[0,0,i,k] = -2*log(abs(V1[i,k]))
            G[1,1,i,k] = -2*log(abs(V2[i,k]))
            G[0,1,i,k] = log(V12[i,k]/np.conjugate(V1[i,k])/V2[i,k])
            G[1,0,i,k] = np.conjugate(G[0,1,i,k])
            
    print()
    # return Gij
    if return_grid:
        return G, evals[:,:,n0:n0+fill], x, y
    else:
        return G, evals[:,:,n0:n0+fill]


def quantum_geometric_tensor_sparse(hamiltonian, kx0, kx1, ky0, ky1, Nk=51, Ef=0.0, n=2, return_grid=False):
    ''' computes the quantum geometric tensor Gij of a 2D system on a square grid for n bands
        around the Fermi level Ef.
        The endpoints of the grid (top and right) are excluded.
        
        The larger interval max([kx0,kx1],[ky0,ky1]) is divided into Nk segements of 
        length dk. The shorter interval of length K is divided into int(K/dk)
        segments.
        
        The Berry curvature is F12 = 2*Im(Gij[0,1]).
        The Fubini-Study metric is gij = Re(Gij).             
    
        hamiltonian: function that returns the Hamiltonian matrix
        Nk: maximum number of grid points along x or y
        kx0,kx1,ky0,ky1: limits of the rectangular kspace grid.
        Ef: Fermi energy
        n: number of considered bands around Ef
        return_grid: if True, the grid point arrays for kx and ky are returned
        
        returns: Gij, evals (optional: kxs, kys)
    '''
    dim = np.shape(hamiltonian(0, 0))[0]
    
    # for sparse diagonalization
    eps_shift=1e-8
    max_steps=10
        
    # ensure that the unit plaquette is a square
    if abs(kx1-kx0) > abs(ky1-ky0):
        Nkx = Nk
        x, step = np.linspace(kx0, kx1, Nkx+1, endpoint=True, retstep=True)
        Nky = int(abs(ky1-ky0)//step)
        y = np.array([(ky0 + i*step) for i in range(Nky+1)])
    elif abs(kx1-kx0) == abs(ky1-ky0):
        Nkx = Nk
        Nky = Nk
        x = np.linspace(kx0, kx1, Nkx+1, endpoint=True)
        y = np.linspace(ky0, ky1, Nky+1, endpoint=True)
    else:
        Nky = Nk
        y, step = np.linspace(ky0, ky1, Nky+1, endpoint=True, retstep=True)
        Nkx = int(abs(kx1-kx0)//step)
        x = np.array([(kx0 + i*step) for i in range(Nkx+1)])

    evecs = np.zeros((Nkx+1,Nky+1,dim,n),dtype=complex)
    evals = np.zeros((Nkx+1,Nky+1,n))
    V1 = np.zeros((Nkx,Nky),dtype=complex)
    V2 = np.zeros((Nkx,Nky),dtype=complex)
    V12 = np.zeros((Nkx,Nky),dtype=complex)
    G = np.zeros((2,2,Nkx,Nky),dtype=complex)

    V1temp = np.zeros((n,n),dtype=complex)
    V2temp = np.zeros((n,n),dtype=complex)
    V12temp = np.zeros((n,n),dtype=complex)
    
    # compute eigenstates of the systems on the grid
    for i in range(Nkx+1):
        print("\rCompute eigenstates: {:3d}/100".format(int((i+1)/(Nkx+1)*100)), end='')
        for k in range(Nky+1):
            ham = hamiltonian(x[i],y[k])
            for l in range(max_steps):
                sigma = Ef + l*eps_shift
                if np.linalg.cond(ham - sigma*np.eye(np.shape(ham)[0])) < 1/sys.float_info.epsilon:
                    # check if matrix shifted by sigma is singular
                    evals[i,k,:], evecs[i,k,:,:] = sla.eigsh(ham, k=n, sigma=sigma, which='LM')
                    sorted_indices = np.argsort(evals[i,k,:])
                    evals[i,k,:] = evals[i,k,sorted_indices]
                    evecs[i,k,:,:] = np.transpose(evecs[i,k,:,sorted_indices])
                    break
                else:
                    continue      
                    
    print()
    # compute link variable on the grid
    for i in range(Nkx):
        print("\rCompute link variables: {:3d}/100".format(int((i+1)/(Nkx)*100)), end='')
        for k in range(Nky):
            for l in range(n):
                for m in range(n):
                    V1temp[l,m] = np.dot(np.conjugate(evecs[i,k,:,l]),evecs[i+1,k,:,m])
                    V2temp[l,m] = np.dot(np.conjugate(evecs[i,k,:,l]),evecs[i,k+1,:,m])
                    V12temp[l,m] = np.dot(np.conjugate(evecs[i+1,k,:,l]),evecs[i,k+1,:,m])                    
            V1[i,k] = linalg.det(V1temp, overwrite_a=True)
            V2[i,k] = linalg.det(V2temp, overwrite_a=True)
            V12[i,k] = linalg.det(V12temp, overwrite_a=True)
            
    print()
    # compute a lattice field strength on the grid
    for i in range(Nkx):
        print("\rCompute quantum geometric tensor: {:3d}/100".format(int((i+1)/(Nkx)*100)), end='')
        for k in range(Nky):
            G[0,0,i,k] = -2*log(abs(V1[i,k]))
            G[1,1,i,k] = -2*log(abs(V2[i,k]))
            G[0,1,i,k] = log(V12[i,k]/np.conjugate(V1[i,k])/V2[i,k])
            G[1,0,i,k] = np.conjugate(G[0,1,i,k])
            
    print()
    # return Gij
    if return_grid:
        return G, evals, x, y
    else:
        return G, evals


def spectral_function_2D(xy, Ham, Ef=0.0, eps=0.05, sparse=False, k=8, eps_shift=1e-8, max_steps=10):
    """ returns the spectral function of the Bloch Hamiltonian Ham(x,y) at the Fermi level Ef. 
        xy is a 2-tupel corresponding to the point in the 2D BZ.
        eps is a parameter of the Green's function.
        
        If sparse is True, only the k closest eigenvalues around Ef are taken into account for the calculation.
        In case there is a convergence issue due to (Ham-Ef) being singular at (xy), Ef is shifted infinitesimally
        by eps_shift up to max_steps times.
    """
    kx, ky = xy
    
    if sparse==True:
        matrix = Ham(kx,ky)
        for l in range(max_steps):
            sigma = Ef + l*eps_shift
            if np.linalg.cond(matrix - sigma*np.eye(np.shape(matrix)[0])) < 1/sys.float_info.epsilon:
                # check if matrix shifted by sigma is singular
                energies = sla.eigsh(matrix, k=k, sigma=sigma, which='LM', return_eigenvectors=False)
                break
            else:
                continue      
    else:
        energies = np.linalg.eigvalsh(Ham(kx,ky))
        
    return np.imag(sum(1./(energies - Ef - 1j*eps)))

def density(evec, orbs):
    ''' Computes the local density of an eigenstate along one direction. The dimension 
        of the local Hilbert space is given by the number of local orbitals orbs.       
    '''
    N = len(evec)//orbs
    density = np.zeros(N)
    for i in range(orbs):
        density += np.abs(evec[i::orbs])**2
    return density


def compute_bands_2D(Ham, params, k_points, Nk=100):
    ''' Computes the bands of a Hamiltonian along lines connecting
        given points in a 2D BZ (such as high-symmetry points)
        
        Ham: Hamiltonian function of the form H(kx, ky, **kwargs)
        k_points: list of 2-component vectors
        Nk: number of grid points for each line connecting adjacent k points
        
        Returns: kline, energies, evecs
    '''
    
    dim = np.shape(Ham(0, 0, **params))[0]
    Np = len(k_points)
    energies_list = []
    evecs_list = []
    klines_list = []

    for i in range(Np-1):
        energies = np.zeros((Nk + (i==Np-2), dim))
        evecs = np.zeros((Nk + (i==Np-2), dim, dim), dtype=complex)       
        kx0, ky0 = k_points[i]
        kx1, ky1 = k_points[i+1]      
        kvec = np.array([kx1-kx0,ky1-ky0])/Nk
        kline = np.linspace(0., np.linalg.norm(kvec)*Nk, Nk+1, endpoint=True)
        for k in range(Nk + (i==Np-2)):
            energies[k,:], evecs[k,:,:] = np.linalg.eigh(Ham(kx0 + kvec[0]*k, 
                                                             ky0 + kvec[1]*k, **params))
        energies_list.append(energies)
        evecs_list.append(evecs)
        if i>0: 
            kline += klines_list[i-1][-1]
            klines_list[i-1] = np.delete(klines_list[i-1], -1)
        klines_list.append(kline)

    kline = klines_list[0]
    energies = energies_list[0]
    evecs = evecs_list[0]
    
    for i in range(Np-2):
        kline = np.concatenate((kline,klines_list[i+1]))
        energies = np.concatenate((energies,energies_list[i+1]))
        evecs = np.concatenate((evecs,evecs_list[i+1]))
    
    return kline, energies, evecs


def plot_bands_2D(kline, energies, k_labels, ymin=None, ymax=None, 
                  linecolor='b', label=None, figsize=(16,8)):
    ''' Plots the bands of a Hamiltonian along lines connecting
        given points in a 2D BZ (such as high-symmetry points)
        obtained from compute_bands_2D
        
        kline: path through the BZ
        energies: array containing the bands along kline
        k_labels: list of strings for names of the k points
        ymin, ymax: plotting range for energies
    '''
    
    plt.figure(figsize=figsize)
    
    dim = np.shape(energies)[1]
    Np = len(k_labels)
    Nk = np.shape(energies)[0]//(Np-1)

    plt.axhline(0.0, color='k')
    plt.plot(kline, energies[:,0], color=linecolor, label=label);
    for i in range(dim-1): plt.plot(kline, energies[:,i+1], color=linecolor);
    for i in range(1,Np-1): plt.axvline(kline[Nk*i], color='k')
           
    plt.xticks([kline[Nk*i] for i in range(Np)], k_labels)
    plt.xlabel("$k$")
    plt.ylabel("$E$")
    if ymin!=None and ymax!=None:
        plt.ylim(ymin,ymax)
    plt.xlim(kline.min(),kline.max())
    

def compute_bands_3D(Ham, params, k_points, Nk=100):
    ''' Computes the bands of a Hamiltonian along lines connecting
        given points in a 3D BZ (such as high-symmetry points)
        
        Ham: Hamiltonian function of the form H(kx, ky, **kwargs)
        k_points: list of 3-component vectors
        Nk: number of grid points for each line connecting adjacent k points
        
        Returns: kline, energies, evecs
    '''
    
    dim = np.shape(Ham(0, 0, 0, **params))[0]
    Np = len(k_points)
    energies_list = []
    evecs_list = []
    klines_list = []

    for i in range(Np-1):
        energies = np.zeros((Nk + (i==Np-2), dim))
        evecs = np.zeros((Nk + (i==Np-2), dim, dim), dtype=complex)       
        kx0, ky0, kz0 = k_points[i]
        kx1, ky1, kz1 = k_points[i+1]      
        kvec = np.array([kx1-kx0,ky1-ky0,kz1-kz0])/Nk
        kline = np.linspace(0., np.linalg.norm(kvec)*Nk, Nk+1, endpoint=True)
        for k in range(Nk + (i==Np-2)):
            energies[k,:], evecs[k,:,:] = np.linalg.eigh(Ham(kx0 + kvec[0]*k, 
                                                             ky0 + kvec[1]*k, 
                                                             kz0 + kvec[2]*k, **params))
        energies_list.append(energies)
        evecs_list.append(evecs)
        if i>0: 
            kline += klines_list[i-1][-1]
            klines_list[i-1] = np.delete(klines_list[i-1], -1)
        klines_list.append(kline)

    kline = klines_list[0]
    energies = energies_list[0]
    evecs = evecs_list[0]
    
    for i in range(Np-2):
        kline = np.concatenate((kline,klines_list[i+1]))
        energies = np.concatenate((energies,energies_list[i+1]))
        evecs = np.concatenate((evecs,evecs_list[i+1]))
    
    return kline, energies, evecs


def plot_bands_3D(kline, energies, k_labels, ymin=None, ymax=None, 
                  linecolor='b', label=None, figsize=(16,8)):
    ''' Plots the bands of a Hamiltonian along lines connecting
        given points in a 3D BZ (such as high-symmetry points)
        obtained from compute_bands_3D
        
        kline: path through the BZ
        energies: array containing the bands along kline
        k_labels: list of strings for names of the k points
        ymin, ymax: plotting range for energies
    '''
    
    plt.figure(figsize=figsize)
    
    dim = np.shape(energies)[1]
    Np = len(k_labels)
    Nk = np.shape(energies)[0]//(Np-1)

    plt.axhline(0.0, color='k')
    plt.plot(kline, energies[:,0], color=linecolor, label=label);
    for i in range(dim-1): plt.plot(kline, energies[:,i+1], color=linecolor);
    for i in range(1,Np-1): plt.axvline(kline[Nk*i], color='k')
           
    plt.xticks([kline[Nk*i] for i in range(Np)], k_labels)
    plt.xlabel("$k$")
    plt.ylabel("$E$")
    if ymin!=None and ymax!=None:
        plt.ylim(ymin,ymax)
    plt.xlim(kline.min(),kline.max())

def imshow_extent(x, y):
    ''' Returns the correct extent values for plotting a function f(x,y) with
        pyplot.imshow(f.transpose(), extent=imshow_extent(x,y)).
    '''
    dx = (x[1]-x[0])/2
    dy = (y[1]-y[0])/2
    return (x[0]-dx,x[-1]+dx,y[0]-dy,y[-1]+dy)