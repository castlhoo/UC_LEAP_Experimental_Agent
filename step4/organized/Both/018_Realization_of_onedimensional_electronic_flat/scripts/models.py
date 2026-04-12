import kwant
import numpy as np

from numpy import cos, sin, pi, exp, sqrt

from scipy.special import j0,k0

import scipy.integrate as integrate

from numpy.linalg import norm

s0 = np.eye(2)
sx = np.array([[0, 1], [1, 0]])
sy = np.array([[0, -1j], [1j, 0]])
sz = np.array([[1, 0], [0, -1]])


#########################################
############## Toy model ################
#########################################

def H0(kx, ky, kz, t1, t2, t=1., d=1.):
    ''' returns the tight-binding Hamiltonian of the unstrained toy model
        at momentum (kx,ky,kz).
        
    '''
    return (6.*t - t1 - 2.*t*cos(d*kx) - 2.*t*cos(d*ky) - 2.*t*cos(d*kz))*sz + 2.*t2*sin(d*kz)*sx


def H_strain(kx, ky, Lz, R, t1, t2, t=1., d=1., spin=False):
    ''' Returns the tight-binding Hamiltonian of the strained toy model
        for a supercell of Lz sites at momentum (kx,ky).
        
        If spin=True, the local basis is 4dim (spin x orbital). Otherwise the local
        basis is 2dim (orbital).
        
        The line z=0 goes through the center of the slab:
        for Lz even: z=0 is between the two central sites
        for Lz odd: z=0 is at the central site.
    '''
    
    if spin:
        
        H_strain = np.zeros((4*Lz,4*Lz), dtype='complex')

        # uniform diagonal terms
        for i in range(Lz):
            H_strain[4*i:4*i+4, 4*i:4*i+4] = np.kron(s0,(6.*t - t1 - 2.*t*cos(d*ky))*sz)

        # hopping terms
        hopp = np.zeros((4*Lz,4*Lz), dtype='complex')
        for i in range(Lz-1):
            hopp[4*i:4*i+4, 4+4*i:4+4*i+4] = np.kron(s0,-sz*t - 1j*t2*sx)
        H_strain += hopp + np.conjugate(np.transpose(hopp))

        # non-uniform diagonal terms
        for i in range(Lz):
            H_strain[4*i:4*i+4, 4*i:4*i+4] += np.kron(s0,-2.*(1.-(i-(Lz-1)/2.)*d/R)*t*cos(d*kx)*sz)
        
    else:
    
        H_strain = np.zeros((2*Lz,2*Lz), dtype='complex')

        # uniform diagonal terms
        for i in range(Lz):
            H_strain[2*i:2*i+2, 2*i:2*i+2] = (6.*t - t1 - 2.*t*cos(d*ky))*sz

        # hopping terms
        hopp = np.zeros((2*Lz,2*Lz), dtype='complex')
        for i in range(Lz-1):
            hopp[2*i:2*i+2, 2+2*i:2+2*i+2] = -sz*t - 1j*t2*sx
        H_strain += hopp + np.conjugate(np.transpose(hopp))

        # non-uniform diagonal terms
        for i in range(Lz):
            H_strain[2*i:2*i+2, 2*i:2*i+2] += -2.*(1.-(i-(Lz-1)/2.)*d/R)*t*cos(d*kx)*sz
            
    return H_strain

def H_strain_no_chiral(kx, ky, Lz, R, mu, t0, t1, t2, t=1., d=1., spin=False):
    ''' Returns the tight-binding Hamiltonian of the strained toy model with
        broken chiral symmetry for a supercell of Lz sites at momentum (kx,ky).
        
        If spin=True, the local basis is 4dim (spin x orbital). Otherwise the local
        basis is 2dim (orbital).
        
        The line z=0 goes through the center of the slab:
        for Lz even: z=0 is between the two central sites
        for Lz odd: z=0 is at the central site.
    '''
    
    if spin:
        
        H_strain = np.zeros((4*Lz,4*Lz), dtype='complex')

        # uniform diagonal terms
        for i in range(Lz):
            H_strain[4*i:4*i+4, 4*i:4*i+4] = np.kron(s0,(6.*t - t1 - 2.*t*cos(d*ky))*sz
                                                    + 2.*t0*cos(d*ky)*s0)

        # hopping terms
        hopp = np.zeros((4*Lz,4*Lz), dtype='complex')
        for i in range(Lz-1):
            hopp[4*i:4*i+4, 4+4*i:4+4*i+4] = np.kron(s0,-sz*t - 1j*t2*sx)
        H_strain += hopp + np.conjugate(np.transpose(hopp))

        # non-uniform diagonal terms
        for i in range(Lz):
            H_strain[4*i:4*i+4, 4*i:4*i+4] += np.kron(s0,-2.*(1.-(i-(Lz-1)/2.)*d/R)*t*cos(d*kx)*sz
                                                     + 2.*(1.-(i-(Lz-1)/2.)*d/R)*t0*cos(d*kx)*s0)
        
    else:
    
        H_strain = np.zeros((2*Lz,2*Lz), dtype='complex')

        # uniform diagonal terms
        for i in range(Lz):
            H_strain[2*i:2*i+2, 2*i:2*i+2] = (6.*t - t1 - 2.*t*cos(d*ky))*sz + 2.*t0*cos(d*ky)*s0

        # hopping terms
        hopp = np.zeros((2*Lz,2*Lz), dtype='complex')
        for i in range(Lz-1):
            hopp[2*i:2*i+2, 2+2*i:2+2*i+2] = -sz*t - 1j*t2*sx
        H_strain += hopp + np.conjugate(np.transpose(hopp))

        # non-uniform diagonal terms
        for i in range(Lz):
            H_strain[2*i:2*i+2, 2*i:2*i+2] += (-2.*(1.-(i-(Lz-1)/2.)*d/R)*t*cos(d*kx)*sz
                                               + 2.*(1.-(i-(Lz-1)/2.)*d/R)*t0*cos(d*kx)*s0)
            
    return H_strain - mu*np.eye(np.shape(H_strain)[0])

def H_strain_ferro(kx, ky, Lz, R, t1, t2, B, order_parameter = np.kron(sz,sy)):
    ''' Returns the tight-binding Hamiltonian of the strained toy model
        for a supercell of Lz sites at momentum (kx,ky) with magnetic
        on-site order of magnitude B.
        
        Energies are in units of t, length scales in units of the lattice constant d.        
        
        The order_parameter can be defined separately. 
        
        The line z=0 goes through the center of the slab:
        for Lz even: z=0 is between the two central sites
        for Lz odd: z=0 is at the central site.
    '''
    H_strain = np.zeros((4*Lz,4*Lz), dtype='complex')
    
    # uniform diagonal terms
    for i in range(Lz):
        H_strain[4*i:4*i+4, 4*i:4*i+4] = (np.kron(s0,(6. - t1 - 2.*cos(ky))*sz)
                                          + B*order_parameter)
    
    # hopping terms
    hopp = np.zeros((4*Lz,4*Lz), dtype='complex')
    for i in range(Lz-1):
        hopp[4*i:4*i+4, 4+4*i:4+4*i+4] = np.kron(s0,-sz - 1j*t2*sx)
    H_strain += hopp + np.conjugate(np.transpose(hopp))
    
    # non-uniform diagonal terms
    # the line z=0 goes through the center of the slab:
    # for Lz even: z=0 is between the two central sites
    # for Lz odd: z=0 is at the central site.
    for i in range(Lz):
        H_strain[4*i:4*i+4, 4*i:4*i+4] += np.kron(s0,-2.*(1.-(i-(Lz-1)/2.)/R)*cos(kx)*sz)
            
    return H_strain


def H_strain_sc(kx, ky, Lz, R, t1, t2, mu, Delta, ldos):
    ''' Returns the BdG Hamiltonian of the strained toy model
        for a supercell of Lz sites at momentum (kx,ky) with 
        superconducting s-wave order of magnitude Delta and 
        chemical potential mu.
        
        Energies are in units of t, length scales in units of the lattice constant d.        
        
        The order parameter is weighted locally with the local
        density of states ldos.
        
        
        The line z=0 goes through the center of the slab:
        for Lz even: z=0 is between the two central sites
        for Lz
    '''
    
    # electron-hole, z position, spin, orbital    
    
    #### e-e block
    H_ee = H_strain(kx, ky, Lz, R, t1, t2, spin=True) - mu*np.eye(4*Lz)
    
    #### h-h block
    H_hh = -(H_strain(kx, ky, Lz, R, t1, t2, spin=True) - mu*np.eye(4*Lz)) # time-reversal symmetry of H0
    
    #### e-h block
    H_eh = np.zeros((4*Lz,4*Lz), dtype=complex)
    Delta_block = Delta*np.kron(sx, s0)
    for i in range(Lz):
        H_eh[4*i:4*i+4, 4*i:4*i+4] = Delta_block*ldos[i]
    
    H_strain_sc = np.block([[H_ee, H_eh],
                         [np.transpose(np.conjugate(H_eh)),H_hh]])
            
    return H_strain_sc

def compute_lD(t, t1, d, R):
    '''Computes lD of the toy model in units of Angstrom (0.1 nm)
       
       t, t1: hopping parameters in eV
       d: lattice constant in Angstrom
       R: curvature radius in Angstrom     
    '''
    Q = sqrt(t1/t)/d
    return sqrt(R*Q)*d

def compute_l0(t, t2, d, R):
    '''Computes l0 of the toy model in units of Angstrom (0.1 nm)
       
       t, t2: hopping parameters in eV
       d: lattice constant in Angstrom
       R: curvature radius in Angstrom     
    '''
    return sqrt(t2*d*R/t)

def compute_V0(t1, t2, R, rmax=20., limit=1000):
    ''' Computes the momentum integral in the ferromagnetic mean-field equations in units of the Coulomb factor V_C.
        V_C is defined in terms of l0: 
        
        V_C = 1/(4*pi*eps*eps0) * 1/l0
    
        R: curvature radius (in l0)
        t1, t2: model parameters (in units of t)
        rmax: upper bound for the r integration (in l0)
        limit: maximum number of iterations for the numerical integration (quad)    
    '''
    
    Q = sqrt(t1)*t2*R
    lD = sqrt(Q/R)/t2
    
    qmin = -np.inf
    qmax = +np.inf
    
    rmin = 0.
    
    def func_q(r):
        return (integrate.quad(lambda q: exp(-lD**4 * q**2 /2) * j0((Q+q)*r), qmin, qmax,limit=limit))[0]
    
    def func_r(r):
        if r <= 20.:
            return r * func_q(r) * exp(r**2/4) * k0(r**2/4) * j0(Q*r)
        else:
            # replace exp(r**2/4)*k0(r**2/4) by leading order term of asymptotic series ~1/r
            return func_q(r) * sqrt(2*pi) * j0(Q*r)
    
    integral, err = integrate.quad(func_r, rmin, rmax, limit=limit)
    
    return sqrt(1./(2*pi))*Q*integral, err

def compute_G0(t1, t2, R, g):
    ''' Computes the momentum integral in the superconducting mean-field equations in units of the Coulomb factor V_C.
        V_C is defined in terms of l0: 
        
        V_C = 1/(4*pi*eps*eps0) * 1/l0
    
        R: curvature radius (in l0)
        t1, t2: model parameters (in units of t)
        g: attractive on-site interaction in units of V_C * l0^3
    '''
    
    Q = sqrt(t1)*t2*R
    lD = sqrt(Q/R)/t2
    
    return 1./(2*pi) * Q/(lD**2) * g

def compute_VC(eps, l0):
    ''' Computes the Coulomb factor VC in eV as defined for the ferromagnetic mean-field equations.
        
        eps: relative dielectric constant (in units of eps0)
        l0: in units of Angstrom
    '''
    return 14.3996/l0/eps

#########################################
####### Rhombohedral graphite ###########
#########################################


def H0_rhombo_graphite(kx, ky, kz, mu, gamma0, gamma1, gamma2, gamma3, gamma4, a=1., b=1.):
    ''' returns the tight-binding Hamiltonian of unstrained rhombohedral graphite
        at momentum (kx,ky,kz).
        
        gamma_i are the parameters of the model
        mu is the chemical potential
        a and b are the lattice constants (a - in-plane, b - out-of-plane) 
    '''
    
    delta1 = a/2*np.array([1., sqrt(3), 0.])
    delta2 = a/2*np.array([1., -sqrt(3), 0.])
    delta3 = a*np.array([-1., 0., 0.])
    
    a1 = a/2*np.array([3., sqrt(3.), 0.])
    a2 = a/2*np.array([3., -sqrt(3.), 0.])
    
    n1 = a1
    n2 = -a1
    n3 = a2
    n4 = -a2
    n5 = a2-a1
    n6 = a1-a2
    
    k_vec = np.array([kx,ky,kz])
    
    delta_sum_plus = exp(1j*(delta1@k_vec)) + exp(1j*(delta2@k_vec)) + exp(1j*(delta3@k_vec))
    delta_sum_minus = exp(-1j*(delta1@k_vec)) + exp(-1j*(delta2@k_vec)) + exp(-1j*(delta3@k_vec))
    n_sum = (exp(1j*(n1@k_vec)) + exp(1j*(n2@k_vec)) + exp(1j*(n3@k_vec))
             + exp(1j*(n4@k_vec)) + exp(1j*(n5@k_vec)) + exp(1j*(n6@k_vec)))
    
    phi_k = (-gamma0 * delta_sum_plus - gamma1 * exp(1j*b*kz) 
             -gamma3 * exp(-1j*b*kz) * delta_sum_minus)
    
    theta_k = (-gamma2*n_sum - gamma4*(exp(1j*kz*b)*delta_sum_minus + exp(-1j*kz*b)*delta_sum_plus))
    
    H0 = np.array([[theta_k, phi_k],[np.conj(phi_k), theta_k]], dtype=complex)
    
    return H0 - mu*np.eye(2)

def H_strain_rhombo_graphite(kx, ky, Lz, R, mu, gamma0, gamma1, gamma2, gamma3, gamma4, alpha=0, a=1., b=1.):
    ''' returns the tight-binding Hamiltonian of strained rhombohedral graphite (ABC stacking)
        for a supercell of Lz sites at momentum (kx,ky).
        
        The line z=0 goes through the center of the slab:
        for Lz even: z=0 is between the two central sites
        for Lz odd: z=0 is at the central site.
        
        gamma_i are the parameters of the model
        mu is the chemical potential
        a and b are the lattice constants (a - in-plane, b - out-of-plane) 
        
        The angle alpha can be used to change the strain axis of the cylindrical substrate.
        alpha = 0:    x axis
        alpha = pi/2: y axis 
    '''
    
    d = 2 # matrix dimension
    
    H_strain = np.zeros((d*Lz,d*Lz), dtype='complex')
    
    delta1 = a/2*np.array([1., sqrt(3)])
    delta2 = a/2*np.array([1., -sqrt(3)])
    delta3 = a*np.array([-1., 0.])
    
    x_dir = np.array([cos(alpha), sin(alpha)])
    
    a1 = a/2*np.array([3., sqrt(3.)])
    a2 = a/2*np.array([3., -sqrt(3.)])
    
    n1 = a1
    n2 = -a1
    n3 = a2
    n4 = -a2
    n5 = a2-a1
    n6 = a1-a2
    
    k_vec = np.array([kx, ky])
    
    gamma0_terms = np.zeros(Lz, dtype='complex')
    gamma2_terms = np.zeros(Lz, dtype='complex')
    gamma3_terms = np.zeros(Lz, dtype='complex')
    gamma4_terms = np.zeros(Lz, dtype='complex')

    for i in range(Lz):
        gamma0_terms[i] = (exp(1j*(delta1@k_vec)) * (1.-(i-(Lz-1)/2.)*b/R * ((delta1@x_dir)/(norm(delta1)))**2)
                           + exp(1j*(delta2@k_vec)) * (1.-(i-(Lz-1)/2.)*b/R * ((delta2@x_dir)/(norm(delta2)))**2)
                           + exp(1j*(delta3@k_vec)) * (1.-(i-(Lz-1)/2.)*b/R * ((delta3@x_dir)/(norm(delta3)))**2))
        gamma2_terms[i] = (exp(1j*(n1@k_vec)) * (1.-(i-(Lz-1)/2.)*b/R * ((n1@x_dir)/(norm(n1)))**2)
                           + exp(1j*(n2@k_vec)) * (1.-(i-(Lz-1)/2.)*b/R * ((n2@x_dir)/(norm(n2)))**2)
                           + exp(1j*(n3@k_vec)) * (1.-(i-(Lz-1)/2.)*b/R * ((n3@x_dir)/(norm(n3)))**2)
                           + exp(1j*(n4@k_vec)) * (1.-(i-(Lz-1)/2.)*b/R * ((n4@x_dir)/(norm(n4)))**2)
                           + exp(1j*(n5@k_vec)) * (1.-(i-(Lz-1)/2.)*b/R * ((n5@x_dir)/(norm(n5)))**2)
                           + exp(1j*(n6@k_vec)) * (1.-(i-(Lz-1)/2.)*b/R * ((n6@x_dir)/(norm(n6)))**2))
        gamma3_terms[i] = (exp(1j*(delta1@k_vec)) * (1.-((i+1)/2-(Lz-1)/2.)*b/R * 
                                                     (delta1@x_dir)**2/(delta1@delta1 + b**2))
                           + exp(1j*(delta2@k_vec)) * (1.-((i+1)/2-(Lz-1)/2.)*b/R * 
                                                       (delta2@x_dir)**2/(delta2@delta2 + b**2))
                           + exp(1j*(delta3@k_vec)) * (1.-((i+1)/2-(Lz-1)/2.)*b/R * 
                                                       (delta3@x_dir)**2/(delta3@delta3 + b**2)))
        gamma4_terms[i] = (exp(-1j*(delta1@k_vec)) * (1.-((i+1)/2-(Lz-1)/2.)*b/R * 
                                                      (delta1@x_dir)**2/(delta1@delta1 + b**2))
                           + exp(-1j*(delta2@k_vec)) * (1.-((i+1)/2-(Lz-1)/2.)*b/R * 
                                                        (delta2@x_dir)**2/(delta2@delta2 + b**2))
                           + exp(-1j*(delta3@k_vec)) * (1.-((i+1)/2-(Lz-1)/2.)*b/R * 
                                                        (delta3@x_dir)**2/(delta3@delta3 + b**2)))
                                                                                                              
    # diagonal terms
    for i in range(Lz):
        phi_diag = -gamma0*gamma0_terms[i]
        theta_diag = -gamma2*gamma2_terms[i]
        H_strain[d*i:d*i+d, d*i:d*i+d] = np.array([[theta_diag, phi_diag],
                                                   [np.conj(phi_diag), theta_diag]], dtype=complex)
        
    # hopping terms
    hopp = np.zeros((d*Lz,d*Lz), dtype='complex')
    for i in range(Lz-1):
        phi_hop_AB = -gamma1
        phi_hop_BA = -gamma3*gamma3_terms[i]
        theta_hop = -gamma4*gamma4_terms[i]
        hopp[d*i:d*i+d, d+d*i:d+d*i+d] = np.array([[theta_hop, phi_hop_AB],
                                                   [phi_hop_BA, theta_hop]], dtype=complex)
    H_strain += hopp + np.conjugate(np.transpose(hopp))
          
    return H_strain - mu*np.eye(d*Lz)  