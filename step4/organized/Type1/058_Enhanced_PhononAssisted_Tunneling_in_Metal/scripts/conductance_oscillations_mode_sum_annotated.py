import networkx as nx
import numpy as np
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg
from multiprocessing import Pool, Lock
import pickle


#networkx is used as base for graph representation, Directed graph is used 

#pickle is used to save data for further analysis 

#multiprocessing - for parallelisation of conductance calculation for many fluxes


def sample_tbg(n, m, with_positions=True):
    '''This function creates system graph with additional nodes on the left and on the right that are used as contacts
    
    arguments:
    2*n - number of columns of nodes
    m * 3 + (m - 1) + 2 - number of rows 
    
    with positions - whether to add positions as node attributes to the networkx graph
    '''
    H = nx.empty_graph(0, create_using=nx.DiGraph())
    if n == 0 or m == 0:
        return H
    M = m * 3 + (m - 1) + 2  # number of rows
    N = 2 * n  # number of columns -1
    rows = range(M)
    cols = range(N + 1)

    # boundary edges
    for j in rows[1:M]:
        if (j % 4 != 0) and j % 4 != 2:
            H.add_edge((0, j), (1, j - (j % 4) + 2))
            H.add_edge((N - 1, j - (j % 4) + 2), (N, j))
        elif j % 4 == 2:
            H.add_edge((1, j), (0, j))
            H.add_edge((N, j), (N - 1, j))
        elif j != 0 and j != M - 1:
            H.add_edge((2, j), (0, j))
            H.add_edge((N, j), (N - 2, j))

    # bulk edges, diagonals and verticals for the even j-s
    for i in cols[2:N - 1:2]:
        for j in rows[0:M - 3:4]:
            H.add_edge((i - 1, j + 2), (i, j))
            H.add_edge((i, j), (i + 1, j + 2))
            H.add_edge((i - 1, j + 2), (i, j + 4))
            H.add_edge((i, j + 4), (i + 1, j + 2))
            H.add_edge((i + 1, j + 2), (i - 1, j + 2))
    # adding the remaining horizontal edges
    for i in cols[2:N - 3:2]:
        for j in rows[4:M - 1:4]:
            H.add_edge((i + 2, j), (i, j))
    
    # Add position node attributes
    if with_positions:
        ii = (i for i in cols for j in rows)
        jj = (j for i in cols for j in rows)
        # xx = (i/2 for i in cols for j in rows)
        xx = (i / 2.0 for i in cols for j in rows)
        h = np.sqrt(3) / 4
        yy = (h * j for i in cols for j in rows)
        pos = {(i, j): (x, y) for i, j, x, y in zip(ii, jj, xx, yy) if (i, j) in H}
        nx.set_node_attributes(H, pos, 'pos')
    return H



def prepare_dicts_and_b_of_equations_for_graph_multiterminal(Gg, L, W,
                                                             initial_vec_left, initial_vec_right,
                                                             Pd, alpha, f):
    '''
    The algorithm for building the system of equations for given system graph and injected currents into edge modes.  
    This function prepared the dictionaries which contain correspondence between edge and index in the sparse 
    system of equations, also the dictionaries with output indices to restore the output distrivutions, and the right-hand 
    side of the system which is always the same. 
    
    now initial_vec_left, initial_vec_right are sparse or dense matrices with shape (4W, window_width x modes)
    and (4W-2, window_width x modes), or are usual numpy 1D arrays
    
    Parameters:
    Gg - system graph 
    L - system length defined in units of a/2 
    W - size of the system - defined in sqrt(3) a/ 4
    initial_vec_left - matrix or vector with initial distribution of the current injected on the left
    initial_vec_right - matrix or vector with initial distribution of the current injected on the right
    Pd - deflection coefficient in S matrix 
    alpha - parameter quasi-1d of mixing in S-matrix 
    f - left-right scattering parameter, complex 
    
    Returns:
    right_side_vec_b - sparse matrix of vectors of right-hand sides  
    dict_of_edge_number_input - dictionary of correspondence between left-most and right-most incoming edges and index in 
    incoming distributions 
    dict_of_edge_number_variable - dictionary of correspondence between edge and its index in the system of eqquations as variables
    dict_of_edge_number_output_left - dictionary of correspondence between left-most outcoming edges and index in 
    system of equations to find outgoing distrubution  
    dict_of_edge_number_output_right - dictionary of correspondence between right-most outcoming edges and index in 
    system of equations to find outgoing distrubution  
    '''
    
    #check for proper sizes of input vectors 
    if len(initial_vec_left) != 4 * W:
        raise ValueError('wrong size in left - not 4 W')
    if len(initial_vec_right) != 2 * (2 * W - 1):
        raise ValueError('wrong size in right - no 4 W - 2')

    #defining scattering matrix  in one node
    phi = alpha 
    cphi = np.cos(phi)
    sphi = np.sin(phi)
    Pdsq = np.sqrt(Pd)
    fconj = np.conj(f)
    Scatt_node = np.array([[f * cphi, 0, 2 * 1j * Pdsq * sphi, -1j * fconj * sphi, 2 * Pdsq * cphi, 0],
                           [2 * 1j * Pdsq * sphi, f * cphi, 0, 0, -1j * fconj * sphi, 2 * Pdsq * cphi],
                           [0, 2 * 1j * Pdsq * sphi, f * cphi, 2 * Pdsq * cphi, 0, -1j * fconj * sphi],
                           [1j * f * sphi, 0, 2 * Pdsq * cphi, -fconj * cphi, 2 * 1j * Pdsq * sphi, 0],
                           [2 * Pdsq * cphi, 1j * f * sphi, 0, 0, -fconj * cphi, 2 * 1j * Pdsq * sphi],
                           [0, 2 * Pdsq * cphi, 1j * f * sphi, 2 * 1j * Pdsq * sphi, 0, -fconj * cphi]],
                          dtype=complex)

    # creating dictionaries of coordinates - {edge:coordinate}
    # gives correspondence between edge and it's number, for input, matrix and output
    number_of_edges_G = Gg.number_of_edges()

    dict_of_edge_number_input = {}
    dict_of_edge_number_variable = {}
    dict_of_edge_number_output_left = {}
    dict_of_edge_number_output_right = {}

    input_ind = 0
    output_ind = 0
    variable_index = 0
    input_vec_b = np.zeros((8 * W - 2, initial_vec_left.shape[1]), dtype=complex)
    right_side_vec_b = sparse.lil_matrix((2 * number_of_edges_G - 8 * W + 2, initial_vec_left.shape[1]), dtype=complex)

    for edge_i in Gg.edges():
        start, end = edge_i
        if start[0] == 0:
            # filling the dictionary of input coordinates
            dict_of_edge_number_input.update({edge_i: input_ind})
            # fills the input_vec_b accordingly to this dictionary
            input_vec_b[2 * input_ind, :] = initial_vec_left[(start[1] - 1), :]
            input_vec_b[2 * input_ind + 1, :] = initial_vec_left[(start[1] - 1) + 1, :]
            input_ind += 1
        elif start[0] == 2 * L:
            dict_of_edge_number_input.update({edge_i: input_ind})
            # print((start[1]-2))
            input_vec_b[2 * input_ind, :] = initial_vec_right[(start[1] - 2), :]
            input_vec_b[2 * input_ind + 1, :] = initial_vec_right[(start[1] - 2) + 1, :]
            input_ind += 1
        elif end[0] == 0:
            dict_of_edge_number_output_left.update({edge_i: output_ind})
            output_ind += 1
            dict_of_edge_number_variable.update({edge_i: variable_index})
            variable_index += 1
        elif end[0] == 2 * L:
            dict_of_edge_number_output_right.update({edge_i: output_ind})
            output_ind += 1
            dict_of_edge_number_variable.update({edge_i: variable_index})
            variable_index += 1
        else:
            dict_of_edge_number_variable.update({edge_i: variable_index})
            variable_index += 1

    # iteration over nodes to fill the b-side
    for node_i in Gg.nodes():
        inedges = list(Gg.in_edges(node_i))
        outedges = list(Gg.out_edges(node_i))

        if (len(inedges) == 3) and (len(outedges) == 3):
            for outedge in outedges:
                # iteration over out edges, always 3 stuks
                out_edge_index_i = dict_of_edge_number_variable[outedge]
                if (outedge[1][0] < outedge[0][0]) and (outedge[0][1] == outedge[1][1]):
                    i = 0
                    # print(outedge, 'b1')
                elif (outedge[1][0] > outedge[0][0]) and (outedge[0][1] > outedge[1][1]):
                    i = 1
                    # print(outedge, 'b2')
                else:
                    i = 2
                    # print(outedge, 'b3')

                for inedge in inedges:
                    # collecting contributions from modes coming through in-edges
                    # a1 - jj=0
                    # a2 - jj=1
                    # a3 - jj=2
                    if (inedge[1][0] < inedge[0][0]) and (inedge[0][1] == inedge[1][1]):
                        jj = 0
                    elif (inedge[1][0] > inedge[0][0]) and (inedge[0][1] > inedge[1][1]):
                        jj = 1
                    else:
                        jj = 2

                    if inedge in dict_of_edge_number_input:
                        # this is the site where one or two input nodes are connected
                        # inputs are inserted into the right_side_vec_b

                        in_edge_index_jj = dict_of_edge_number_input[inedge]
                        for window_ind in range(initial_vec_left.shape[1]):
                            right_side_vec_b[2 * out_edge_index_i, window_ind] += Scatt_node[i, jj] * \
                                                                                  input_vec_b[
                                                                                      2 * in_edge_index_jj, window_ind]
                            right_side_vec_b[2 * out_edge_index_i + 1, window_ind] += Scatt_node[3 + i, 3 + jj] * \
                                                                                      input_vec_b[
                                                                                          2 * in_edge_index_jj + 1, window_ind]

                            # flavor mixing part
                            right_side_vec_b[2 * out_edge_index_i, window_ind] += Scatt_node[i, 3 + jj] * \
                                                                                  input_vec_b[
                                                                                      2 * in_edge_index_jj + 1, window_ind]
                            right_side_vec_b[2 * out_edge_index_i + 1, window_ind] += Scatt_node[3 + i, jj] * \
                                                                                      input_vec_b[
                                                                                          2 * in_edge_index_jj, window_ind]
    right_side_vec_b = sparse.csc_matrix(right_side_vec_b, dtype=complex)
    return right_side_vec_b, dict_of_edge_number_input, dict_of_edge_number_variable, \
           dict_of_edge_number_output_left, dict_of_edge_number_output_right


def solve_system_of_equations_for_graph_dict_prepared(Gg, L, W, Pd, alpha, f, Energy, Magn_phi, l_unit, velocity,
                                                      right_side_vec_b, dict_of_edge_number_input,
                                                      dict_of_edge_number_variable,
                                                      dense=False):
    '''
    This function creates a system of equations A x = b with two variables per each edge (in single valley) and solve it 
    
    Parameters:
    Gg - system graph 
    L - system length defined in units of a/2 
    W - size of the system - defined in sqrt(3) a/ 4
    Pd - deflection coefficient in S matrix 
    alpha - parameter quasi-1d of mixing in S-matrix 
    f - left-right scattering parameter, complex 
    Energy - energy of injected modes  
    Magn_phi - magnetic flux, see fig 2 in paper for proper definition
    l_unit - length of one edge
    velocity - velocity of the mode on the edge
    right_side_vec_b - right-hand side of the system 
    dict_of_edge_number_input - dictionary of correspondence between left-most and right-most incoming edges and index in 
    incoming distributions 
    dict_of_edge_number_variable - dictionary of correspondence between edge and its index in the system of eqquations as variables 
    dense - whether to use dense matrices or sparse (sparse are mostly always preferable)
    
    
    Returns:
    edge_solution - matrix of solutions for each right-hand side of vector right_side_vec_b, length - number of variable edges
    '''
    def Magn_Phase(st_pos, end_pos):
        # magnetic phase as Peierls one, calculated with A = (0, B x, 0)
        # print('argument of phase',
        #      round(np.imag(-1j*np.pi*Magn_phi*(st_pos[0]+end_pos[0])*(st_pos[1]-end_pos[1])/(2*np.sqrt(3)*l_unit*l_unit/4)), 4))
        return np.exp(-1j * np.pi * Magn_phi * (st_pos[0] + end_pos[0]) * (st_pos[1] - end_pos[1]) / (
                    2 * np.sqrt(3) * l_unit * l_unit / 4))

    #energy phase accumulated during from start to end of edge
    energy_ph = np.exp(-1j * Energy * l_unit / velocity)
    
    #defining scattering matrix  in one node
    phi = alpha 
    cphi = np.cos(phi)
    sphi = np.sin(phi)
    Pdsq = np.sqrt(Pd)
    fconj = np.conj(f)
    Scatt_node = np.array([[f * cphi, 0, 2 * 1j * Pdsq * sphi, -1j * fconj * sphi, 2 * Pdsq * cphi, 0],
                           [2 * 1j * Pdsq * sphi, f * cphi, 0, 0, -1j * fconj * sphi, 2 * Pdsq * cphi],
                           [0, 2 * 1j * Pdsq * sphi, f * cphi, 2 * Pdsq * cphi, 0, -1j * fconj * sphi],
                           [1j * f * sphi, 0, 2 * Pdsq * cphi, -fconj * cphi, 2 * 1j * Pdsq * sphi, 0],
                           [2 * Pdsq * cphi, 1j * f * sphi, 0, 0, -fconj * cphi, 2 * 1j * Pdsq * sphi],
                           [0, 2 * Pdsq * cphi, 1j * f * sphi, 2 * 1j * Pdsq * sphi, 0, -fconj * cphi]],
                          dtype=complex)

    number_of_edges_G = Gg.number_of_edges()

    # define dense or sparse matrix
    if (dense):
        System_matrix = np.identity(2 * number_of_edges_G - 8 * W + 2, dtype=complex)
    else:
        System_matrix = sparse.identity(2 * number_of_edges_G - 8 * W + 2, dtype=complex, format='lil')

    # iteration over nodes to fill the system of equations
    for node_i in Gg.nodes():
        inedges = list(Gg.in_edges(node_i))
        outedges = list(Gg.out_edges(node_i))

        if (len(inedges) == 1) and (len(outedges) == 1):
            in_edge_ind = dict_of_edge_number_variable[inedges[0]]
            out_edge_ind = dict_of_edge_number_variable[outedges[0]]

            coord1 = Gg.nodes[inedges[0][0]]['pos']
            coord2 = Gg.nodes[inedges[0][1]]['pos']

            # System_matrix[2*out_edge_ind, 2*out_edge_ind] = 1.0
            # System_matrix[2*out_edge_ind+1, 2*out_edge_ind+1] = 1.0

            System_matrix[2 * out_edge_ind, 2 * in_edge_ind] = -1.0 * energy_ph * \
                                                               Magn_Phase(coord1, coord2)
            System_matrix[2 * out_edge_ind + 1, 2 * in_edge_ind + 1] = -1.0 * energy_ph * \
                                                                       Magn_Phase(coord1, coord2)
            # print('added boundary condition', (2*out_edge_ind, 2*in_edge_ind),
            # System_matrix[2*out_edge_ind, 2*in_edge_ind])

        # bulk nodes - we check whether edges are keys in input dictionary,
        #             and fill the matrix + optionally right-hand side b
        if (len(inedges) == 3) and (len(outedges) == 3):
            for outedge in outedges:
                # iteration over out edges, always 3 stuks
                out_edge_index_i = dict_of_edge_number_variable[outedge]
                if (outedge[1][0] < outedge[0][0]) and (outedge[0][1] == outedge[1][1]):
                    i = 0
                    # print(outedge, 'b1')
                elif (outedge[1][0] > outedge[0][0]) and (outedge[0][1] > outedge[1][1]):
                    i = 1
                    # print(outedge, 'b2')
                else:
                    i = 2
                    # print(outedge, 'b3')

                System_matrix[2 * out_edge_index_i, 2 * out_edge_index_i] = 1.0
                System_matrix[2 * out_edge_index_i + 1, 2 * out_edge_index_i + 1] = 1.0
                for inedge in inedges:
                    # collecting contributions from modes coming through in-edges
                    # a1 - jj=0
                    # a2 - jj=1
                    # a3 - jj=2
                    if (inedge[1][0] < inedge[0][0]) and (inedge[0][1] == inedge[1][1]):
                        jj = 0
                        # print(jj, 'this is a1, 0?')
                    elif (inedge[1][0] > inedge[0][0]) and (inedge[0][1] > inedge[1][1]):
                        jj = 1
                        # print(jj, 'this is a2, 1?')
                    else:
                        jj = 2

                    if inedge not in dict_of_edge_number_input:
                        in_edge_index_jj = dict_of_edge_number_variable[inedge]

                        coord1 = Gg.nodes[inedge[0]]['pos']
                        coord2 = Gg.nodes[inedge[1]]['pos']
                        # print('coords', inedge, 'magn phase', Magn_Phase(coord1, coord2))

                        # flavor isotropic part
                        System_matrix[2 * out_edge_index_i, 2 * in_edge_index_jj] = -Scatt_node[i, jj] * \
                                                                                    energy_ph * \
                                                                                    Magn_Phase(coord1, coord2)
                        System_matrix[2 * out_edge_index_i + 1, 2 * in_edge_index_jj + 1] = -Scatt_node[3 + i, 3 + jj] * \
                                                                                            energy_ph * \
                                                                                            Magn_Phase(coord1, coord2)

                        # flavor mixing part
                        System_matrix[2 * out_edge_index_i, 2 * in_edge_index_jj + 1] = -Scatt_node[i, 3 + jj] * \
                                                                                        energy_ph * \
                                                                                        Magn_Phase(coord1, coord2)
                        System_matrix[2 * out_edge_index_i + 1, 2 * in_edge_index_jj] = -Scatt_node[3 + i, jj] * \
                                                                                        energy_ph * \
                                                                                        Magn_Phase(coord1, coord2)

                        # print(2*out_edge_index_i, 2*in_edge_index_jj, Scatt_node[i, 2-jj])
                        # print(2*out_edge_index_i+1,2*in_edge_index_jj+1, Scatt_node[3+i, 5-jj])

    '''testing part
    for key in dict_of_edge_number_variable:
        print(key, ' -- ', dict_of_edge_number_variable[key])
    np.set_printoptions(precision=3)
    print(Scatt_node)
    print(System_matrix)
    #print(right_side_vec_b)
    '''

    if (dense):
        edge_solution = np.linalg.solve(System_matrix, right_side_vec_b)
    else:
        System_matrix = sparse.csc_matrix(System_matrix, dtype=complex)
        edge_solution = sparse_linalg.spsolve(System_matrix, right_side_vec_b)
    return edge_solution


def create_init_injection_conductance_left_4_modes(W, window_size):
    '''creates initial vectors on left and right sides with zeros on the right and single modes in given window on the left
    
    this is injection of the current for K valley
    
    window - is a contact to metak regions described in the paper
    
    returns left and right vectors where even index refers to coordinate divided by two (in units of sqrt(3)/2 
    '''
    initial_vec_right = np.zeros((4 * W - 2, 4 * window_size), dtype=complex)
    initial_vec_left = np.zeros((4 * W, 4 * window_size), dtype=complex)
    for i in range(4 * window_size):
        initial_vec_left[2 * W + i - 2 * window_size, i] = 1.0
    # no need for normalization - we already inject 1 into single mode
    return initial_vec_left, initial_vec_right


def create_init_injection_conductance_right_2_modes(W, window_size):
'''creates initial vectors on left and right sides with zeros on the left and single modes in given window on the right
    
    this is injection of the current for K-prime valley
    
    window - is a contact to metak regions described in the paper
    
    returns left and right vectors where even index refers to coordinate divided by two (in units of sqrt(3)/2 
    '''
    initial_vec_right = np.zeros((4 * W - 2, 4 * window_size), dtype=complex)
    initial_vec_left = np.zeros((4 * W, 4 * window_size), dtype=complex)
    for i in range(4 * window_size):
        initial_vec_right[2 * W + i - 2 * window_size, i] = 1.0
    # no need for normalization - we already inject 1 into single mode
    return initial_vec_left, initial_vec_right


def transform_edgedata_to_output_vector(edge_solution, dict_edge_number_variable,
                                        dict_edge_number_output_left, dict_edge_number_output_right):
    '''Transforms solution from graph edges notation to coordinate y in real space notation

    takes output of solve_system_of_equations_for_graph function

    returns two vectors - left solution, right solution
    '''
    # lenght of the left and right vectors is defined from len(dict)
    left_solution = np.zeros(2 * len(dict_edge_number_output_left), dtype=complex)
    right_solution = np.zeros(2 * len(dict_edge_number_output_right), dtype=complex)

    # print(2*len(dict_edge_number_output_left))
    # print(2*len(dict_edge_number_output_right))

    for edge_left in dict_edge_number_output_left:
        left_solution[edge_left[1][1] - 2] = edge_solution[2 * dict_edge_number_variable[edge_left]]
        left_solution[edge_left[1][1] - 2 + 1] = edge_solution[2 * dict_edge_number_variable[edge_left] + 1]

    for edge_right in dict_edge_number_output_right:
        right_solution[(edge_right[1][1] - 1)] = edge_solution[2 * dict_edge_number_variable[edge_right]]
        right_solution[(edge_right[1][1] - 1) + 1] = edge_solution[2 * dict_edge_number_variable[edge_right] + 1]

    return left_solution, right_solution


def calculate_conductance_window_window_transmission(flux_magnetic):
    '''
    function that computes conductance by counting transmission to the given window for each incoming mode and 
    then performs the summation over all independent modes in the incoming window 
    
    version for K-valley
    
    as input takes only magnetic flux, other variables are fixed globally - such as system, sizes, 
    node S-matrix parameters 
    
    returns data in the format [flux_magnetic, np.sum(conductance_backward), np.sum(conductance_forward)]
    and also saves the same data to the temporary file conductance_temp_file_name (to avoid losing data 
    in the case of unexpected external termination) 
    '''
    edge_solution_B = solve_system_of_equations_for_graph_dict_prepared(H_B,
                                                                        L_B, W_B,
                                                                        Pd=Pd, alpha=alpha_fixed, f=f_par,
                                                                        Energy=Energy_par, Magn_phi=flux_magnetic,
                                                                        l_unit=1.0, velocity=1.0,
                                                                        right_side_vec_b=right_side_vec_b_B,
                                                                        dict_of_edge_number_input=dict_input_B,
                                                                        dict_of_edge_number_variable=dict_var_B,
                                                                        dense=False)

    conductance_backward = np.zeros(right_side_vec_b_B.shape[1])
    conductance_forward = np.zeros(right_side_vec_b_B.shape[1])

    for i in range(right_side_vec_b_B.shape[1]):
        edge_solution_B_dense = edge_solution_B.todense()
        sol_left_B, sol_right_B = transform_edgedata_to_output_vector(edge_solution_B_dense[:, i], dict_var_B,
                                                                      dict_out_left_B, dict_out_right_B)

        conductance_backward[i] = (np.linalg.norm(
            sol_left_B[2 * W_B - 2 * output_window_size:2 * W_B + 2 * output_window_size])) ** 2
        conductance_forward[i] = (np.linalg.norm(
            sol_right_B[2 * W_B - 2 * output_window_size:2 * W_B + 2 * output_window_size])) ** 2

    print('done phi', flux_magnetic, np.sum(conductance_backward), np.sum(conductance_forward))

    lock.acquire()
    f = open(conductance_temp_file_name, 'ab')
    pickle.dump([flux_magnetic, np.sum(conductance_backward), np.sum(conductance_forward)], f)
    f.close()
    lock.release()


    return [flux_magnetic, np.sum(conductance_backward), np.sum(conductance_forward)]


def calculate_conductance_window_window_transmission_Kp(flux_magnetic):
    '''
    function that computes conductance by counting transmission to the given window for each incoming mode and 
    then performs the summation over all independent modes in the incoming window 
    
    version for K-prime-valley
    
    as input takes only magnetic flux, other variables are fixed globally - such as system, sizes, 
    node S-matrix parameters 
    
    returns data in the format [flux_magnetic, np.sum(conductance_backward), np.sum(conductance_forward)]
    and also saves the same data to the temporary file conductance_temp_file_name (to avoid losing data 
    in the case of unexpected external termination) 
    '''
    edge_solution_B = solve_system_of_equations_for_graph_dict_prepared(H_B,
                                                                        L_B, W_B,
                                                                        Pd=Pd, phi=phi_fixed, f=f_par,
                                                                        Energy=Energy_par, Magn_phi=flux_magnetic,
                                                                        l_unit=1.0, velocity=1.0,
                                                                        right_side_vec_b=right_side_vec_b_B,
                                                                        dict_of_edge_number_input=dict_input_B,
                                                                        dict_of_edge_number_variable=dict_var_B,
                                                                        dense=False)

    conductance_backward = np.zeros(right_side_vec_b_B.shape[1])
    conductance_forward = np.zeros(right_side_vec_b_B.shape[1])

    for i in range(right_side_vec_b_B.shape[1]):
        edge_solution_B_dense = edge_solution_B.todense()
        sol_left_B, sol_right_B = transform_edgedata_to_output_vector(edge_solution_B_dense[:, i], dict_var_B,
                                                                      dict_out_left_B, dict_out_right_B)

        conductance_forward[i] = (np.linalg.norm(
            sol_left_B[2 * W_B - 2 * output_window_size:2 * W_B + 2 * output_window_size])) ** 2
        conductance_backward[i] = (np.linalg.norm(
            sol_right_B[2 * W_B - 2 * output_window_size:2 * W_B + 2 * output_window_size])) ** 2

    print('done phi', flux_magnetic, np.sum(conductance_backward), np.sum(conductance_forward))

    lock.acquire()
    f = open(conductance_temp_file_name, 'ab')
    pickle.dump([flux_magnetic, np.sum(conductance_backward), np.sum(conductance_forward)], f)
    f.close()
    lock.release()


    return [flux_magnetic, np.sum(conductance_backward), np.sum(conductance_forward)]


def init(l):
    '''initialized function for the multiprocessi Pool, is used to lock writing into temporary file'''
    global lock
    lock = l
    return


# initialization
W_B = 500  # width of the graph
L_B = 250  # length of the graph
H_B = sample_tbg(L_B, W_B) #networkx graph object 

#size of window into which the injection of current is performed. The number of injected modes is 4 times input_window_size
input_window_size = 10 

#size of window in which the measurement is performed. The number of measured modes in 4*output_window_size
output_window_size = 10 

#vectors of injected current from the left and from the right, composed into list for all possible modes in given window
#this is for K-valley
initial_vec_left_B, initial_vec_right_B = create_init_injection_conductance_left_4_modes(W_B, window_size=input_window_size)

#if calculation for K' valley is needed, one should remove comment below
#initial_vec_left_B, initial_vec_right_B = create_init_injection_conductance_right_2_modes(W_B, window_size=input_window_size)

#parameters of node scattering matrices 
Pf1 = 0.25
Pf2 = 0.25
Pd = (1 - Pf1 - Pf2) / 4
f_par=np.sqrt(Pf1)+1j*np.sqrt(Pf2)
alpha_fixed = 0.00


#fixed energy parameter 
Energy_par = 0.0

#right-hand side of the system of equation and dictionaries of edge: index correspondence 
#(they are all same for every magnetic flux)
right_side_vec_b_B, dict_input_B, dict_var_B, dict_out_left_B, dict_out_right_B = prepare_dicts_and_b_of_equations_for_graph_multiterminal(H_B,
                                        L_B, W_B,
                                        initial_vec_left_B, initial_vec_right_B,
                                        Pd=Pd, alpha=alpha_fixed, f=f_par)


conductance_temp_file_name = 'conductance_temp_file.txt'
conductance_file_name = 'conductance_final_file.txt'


print('initialization done')

if __name__ == '__main__':
    #number of processes = number of workers which are started by multiprocessing Pool, should be chosen accordingly to 
    #number of cores and RAM in the system (usually, less that number of cores for best efficiency)
    number_processes = 12
    flux_data = np.linspace(0.00, 0.05, 504)
    
    #replace previous line by this if the calculation in K-prime-valley is needed. The K-prime valley case can be viewed 
    #as inverted system (all edges are inverted), thus injection from the right is the same. The magnetic flux should change the 
    #sign to0, which is taken into account is the line below   
    #flux_data = np.linspace(-0.00, -0.05, 504)
    
    print('started')

    file1 = open(conductance_temp_file_name, 'wb')
    pickle.dump(flux_data, file1)
    pickle.dump([W_B, L_B], file1)
    file1.close()

    l = Lock()
    
    #multiprocessing is used to parallelise calculation on multicore processor 
    pool = Pool(processes=number_processes, initializer=init, initargs=(l,))
    
    #K-valley calculation 
    conductance_results = pool.map(calculate_conductance_window_window_transmission, flux_data)
    
    #uncomment if calculation for K-prime valley is needed
    #conductance_results = pool.map(calculate_conductance_window_window_transmission_Kp, flux_data)
    pool.close()
    pool.join()

    file = open(conductance_file_name, 'wb')
    pickle.dump(flux_data, file)
    pickle.dump(conductance_results, file)
    file.close()

    print('done all')