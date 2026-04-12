#*****************************************************************************************************#
#***************************************** Importing modules *****************************************#
#*****************************************************************************************************#

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from numpy import sin, exp, cos, pi, sqrt
from shapely.geometry import Point, Polygon
from descartes import PolygonPatch
import kwant
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import os
import timeit
import datetime
import dill
import copy
import sys

#******************************************************************************************************#
#***************************************** Defining constants *****************************************#
#******************************************************************************************************#

sin_30, cos_30 = (1. / 2, np.sqrt(3.) / 2) 
a0 = 2.46 # Honeycomb lattice constant (not nearest-neighbors!) [A]
d0 = 3.35 # Distance between the layers [A]
lcon = a0 / np.sqrt(3) # Nearest neighbor constant [A]
R0 = a0 * cos_30 + lcon * sin_30 + lcon # Lattice constant with armchair edges
Vppp = -3.09 # Intralayer hopping for graphene [eV]
Vpps =  -0.39 # Interlayer hopping for AA stacked Bilayer graphene[eV]
chem_pot = -0.009070841623338132 # Chemical potential in the scattering region [eV] (Dirac-point energy at the magic angle)
leads_chem_pot = -2 # Chemical potential of the leads [eV]
lambda0 = 0.27 # Constant necessary for the interlayer hoppings[A]


#******************************************************************************************************#
#******************************* Generate the sample, funtion and class *******************************#
#******************************************************************************************************#

def rotate(angle_deg, vector):

    """ Rotates a 2D or 3D vector around the z-axis.

    Parameters:
    -----------
    angle_deg: float
        Angle of rotation in degrees, starting from the x-axis
    vector: list or NumPy array of length 2 or 3
        Vector to be rotated

    Returns:
    --------
    vector_post: NumPy array of length 2 or 3
        Rotated vector
    """

    angle = np.radians(angle_deg)
    M = np.array([
        [cos(angle),-sin(angle),0],
        [sin(angle),cos(angle),0],
        [0,0,1]
    ])

    if len(vector) == 2:
        return M[0:2,0:2] @ vector
    else:
        return M @ vector
    
class Timer():

    """ 
        My simple timer class to print out the time it takes to run a specific calculation.
    """

    def __init__(self):
        self.time = timeit.default_timer() # Set the timer

    def reset_timer(self, message = None): # Reset the timer and optionally print out a message with the time 
                                           # between the previous set and the reset
        seconds = int(timeit.default_timer() - self.time)
        if message is not None:
            print(message, datetime.timedelta(seconds = seconds))

        self.time = timeit.default_timer()

    def print_timer(self, message):       # Print the timer without reseting it
        seconds = int(timeit.default_timer() - self.time)
        print(message, datetime.timedelta(seconds = seconds))



def create_sample(NL_top, NW_top, N_lead_to_sample, twist_angle_deg, stacking = 'AA', disorder_strength = 0., seed = None, return_vertices_coords = False):
    
    """ Create a twisted bilayer graphene kwant system.

    Parameters:
    -----------
    NL_top, NW_top: int
        Number of armchair translations in length and width of the top layer (the rotated one)
    N_lead_to_sample: int
        Number of armachair translations between the scattering region and the leads
    twist_angle_deg: float
        Relative twist angle between the layers in degrees
    stacking: "AA" or "AB"
        Bilayer graphene stacking at zero rotation
    return_vertices_coords: Bool
        If set to true the function returns the coordinates of the vertices of the sample

    Returns:
    --------
    syst: kwant.system
        Unfinalized kwant system
    vertices_xycoords: list
        Array with the xy coordinates of the vertices of the sample
    """ 
    
    
    #********************************** Creating the bulk of the lattice **********************************#

    NL_bot = NL_top + 2 * N_lead_to_sample # NL_bot
    NW_bot = NW_top - 2 * N_lead_to_sample # NW_bot
    
    if NW_bot < 1:
        raise ValueError('The width of the sample is incompatible with the number of \
                          translations from the leads to the sample!')
    
    a1 = np.array([0,0,0])                    # Atoms in a unit cell
    a2 = np.array([sin_30,-cos_30,0]) * lcon
    a3 = np.array([cos_30,-sin_30,0]) * a0
    a4 = np.array([1,0,0]) * (R0 - lcon)
    a5 = np.array([cos_30,sin_30,0]) * a0
    a6 = np.array([sin_30,cos_30,0]) * lcon
    
    bot_basis = [a1,a2,a3,a4,a5,a6] # Basis of the bottom layer
    
    V1_bot = R0 * np.array([1, 0, 0]) # Primitive vectors 
    V2_bot = R0 * np.array([sin_30,cos_30, 0])
    V1_top = rotate(twist_angle_deg,V1_bot)
    V2_top = rotate(twist_angle_deg,V2_bot)

    v1 = np.array([0,0,d0])
    
    if stacking == "AB":
        v1 += np.array([lcon*sin_30,lcon*cos_30,0])
        
    top_basis = []
    for atom in bot_basis:
        top_basis.append(rotate(twist_angle_deg,atom) + v1)  
        
    bot_lat = kwant.lattice.general([V1_bot,V2_bot],bot_basis,norbs=1) #Lattices    
    top_lat = kwant.lattice.general([V1_top,V2_top],top_basis,norbs=1)
    
    syst = kwant.Builder()
    bot_lead = kwant.Builder(kwant.TranslationalSymmetry(-V1_bot)) # Leads
    top_lead = kwant.Builder(kwant.TranslationalSymmetry(-V2_top))
    
    NL_bot_start = -int(NL_bot / 2) # Starting points (so that the rotation is in the middle of the scattering region)
    NW_bot_start = -int(NW_bot / 2)
    NL_top_start = -int(NL_top / 2)
    NW_top_start = -int(NW_top / 2)
    
    ab,bb,cb,db,eb,fb = bot_lat.sublattices # Sublattices 
    at,bt,ct,dt,et,ft = top_lat.sublattices
    
    #****************************************** Adding the sites ******************************************#    
    
    ymin = -lcon * cos_30 + v1[1] + (NW_top_start * R0 * cos_30)
    ymax = -ymin
    
    displacement = np.array(at(NL_top_start, NW_top + NW_top_start).pos)
    ydif = ymax - displacement[1]
    extra_translations = int(ydif / (R0 * cos_30))

    NW_top_start += - extra_translations
    NW_top += 2 *  extra_translations
    
    
    def site_chem_pot(site):
        x,y,z = site.pos
        if y >= ymin and y <= ymax:
            return chem_pot + np.random.uniform(-disorder_strength , disorder_strength) 
        else:
            return leads_chem_pot
        
    if seed is not None:
        np.random.seed(seed)

    for sublat in [ab, bb, cb, db, eb, fb]:
        for j in range(NW_bot):
            bot_lead[sublat(NL_bot_start, j+NW_bot_start)] = leads_chem_pot
            for i in range(NL_bot):
                syst[sublat(i+NL_bot_start, j+NW_bot_start)] = site_chem_pot
            
    for sublat in [at,bt,ct,dt,et,ft]:
        for i in range(NL_top):
            top_lead[sublat(NL_top_start+i, NW_top_start)] = leads_chem_pot
            for j in range(NW_top):
                syst[sublat(i+NL_top_start, j+NW_top_start)] = site_chem_pot
        
    for sublat in [bb, cb, ab, db]:
        for i in range(NL_bot):
            syst[sublat(i + NL_bot_start, NW_bot + NW_bot_start)] = site_chem_pot
            
    for sublat in [ab, bb, eb, fb]:
        for j in range(NW_bot):
            syst[sublat(NL_bot + NL_bot_start, j + NW_bot_start)] = site_chem_pot

    for sublat in [bb, cb, ab, db]:
        bot_lead[sublat(NL_bot_start, NW_bot + NW_bot_start)] = leads_chem_pot
        
    for sublat in [bt, et, at, ft]:
        for j in range(NW_top):
            syst[sublat(NL_top + NL_top_start, j + NW_top_start)] = site_chem_pot

    for sublat in [bt, ct, at, dt]:
        for i in range(NL_top):
            syst[sublat(i + NL_top_start, NW_top + NW_top_start)] = site_chem_pot

    for sublat in [bt, et, at, ft]:
        top_lead[sublat(NL_top + NL_top_start, NW_top_start)] = leads_chem_pot

    
    #************************************ Adding intralayer hoppings *************************************#

    syst[bot_lat.neighbors()] = Vppp
    bot_lead[bot_lat.neighbors()] = Vppp
    syst[top_lat.neighbors()] = Vppp
    top_lead[top_lat.neighbors()] = Vppp
    
    #**************************************** Attaching the leads ****************************************#


    syst.attach_lead(top_lead.reversed()) # Lead 0: top
    syst.attach_lead(top_lead) # Lead 1: bottom
    # syst.attach_lead(bot_lead) # Lead 2: left
    # syst.attach_lead(bot_lead.reversed()) # Lead 3: right
    
    #************************************ Extracting the sample vertices ************************************#
    
    if not return_vertices_coords:
        return syst
    
    '''
                  Remember the ordering of the vertices:
        
                           3 -------------- 2
                          /                /
                         /                /
                       0,4 ------------- 1         
                       
    '''
    
    vertices_xcoords = [0,0,0,0,0]
    vertices_ycoords = [0,0,0,0,0]
    
    vertices_xcoords[0] = ab(NL_bot_start ,NW_bot_start - N_lead_to_sample).pos[0] 
    vertices_ycoords[0] = ab(NL_bot_start ,NW_bot_start - N_lead_to_sample).pos[1] 
    
    vertices_xcoords[1] = ab(NL_bot_start + NL_bot ,NW_bot_start - N_lead_to_sample).pos[0] 
    vertices_ycoords[1] = ab(NL_bot_start + NL_bot ,NW_bot_start - N_lead_to_sample).pos[1] 
    
    vertices_xcoords[2] = ab(NL_bot_start + NL_bot ,NW_bot_start+NW_bot + N_lead_to_sample).pos[0] 
    vertices_ycoords[2] = ab(NL_bot_start + NL_bot ,NW_bot_start+NW_bot + N_lead_to_sample).pos[1] 
    
    vertices_xcoords[3] = ab(NL_bot_start,NW_bot_start+NW_bot + N_lead_to_sample).pos[0] 
    vertices_ycoords[3] = ab(NL_bot_start,NW_bot_start+NW_bot + N_lead_to_sample).pos[1] 
    
    vertices_xcoords[4] = vertices_xcoords[0]
    vertices_ycoords[4] = vertices_ycoords[0]
    
    vertices_xycoords = np.array([[x,y] for x, y in zip(vertices_xcoords, vertices_ycoords)])
    
    return syst, vertices_xycoords

class TBGSample:
    
    
    def __init__(self, NL, NW, N_lead_to_sample, twist_angle_deg, stacking = 'AA' , disorder_strength = 0, seed = None):
        
        
        self.size = f"{NL}x{NW}"
        self.chem_pot = chem_pot
        self.leads_chem_pot = leads_chem_pot
        self.disorder_strength = disorder_strength
        self.seed = seed

        
        self.system, self.vertices = create_sample(NL, NW, N_lead_to_sample, twist_angle_deg, \
                                                        stacking = 'AA', disorder_strength = disorder_strength, seed = seed, return_vertices_coords = True)
        
        self.length = self.vertices[1][0] - self.vertices[0][0]
        self.width = self.vertices[3][1] - self.vertices[0][1]
        self.position = - self.vertices[0]
        self.domains_polygons = None
        self.scaling_factors = None
        
    #********************** Transform coordinates (to align to the disorder domains) **********************#
    
    def transform_coords(self, xys):
        
        x0, y0 = self.position
        ax, ay = self.scaling_factors
        xys_post = np.zeros(np.shape(xys))

        for i, xy in enumerate(xys):
            y_post = ay * (xy[1] + y0)
            x_post = ax * (xy[0] + x0 - (xy[1] + y0) * np.tan(np.radians(30)))
            xys_post[i] = x_post, y_post

        return xys_post
        
    #******************************************* System plotter *******************************************#
    
    def plot_system(self, plot_subregions = False, plot_fname = None, show_plot = False):
        

        prop_cycle = plt.rcParams['axes.prop_cycle']
        colors = prop_cycle.by_key()['color']
        colors.pop(3)

        def get_site_energy(site):
            if callable(self.system[site]):
                return self.system[site](site)
            return self.system[site]

        def site_color(site):
            
            if self.domains_polygons is None:
                if get_site_energy(site) == self.leads_chem_pot:
                    return 'r'
                return 'k'

            if get_site_energy(site) == self.leads_chem_pot:
                return 'r'
            else:
                x,y,z = site.pos
                x_post, y_post = self.transform_coords([[x, y]])[0]
                pt = Point([x_post,y_post])

                for i in range(len(self.domains_polygons)):
                    if pt.within(self.domains_polygons[i]):
                        return colors[i%9]
            return 'k'

        azim, dist, elev = -90, 8, 90 # Default: -60, 10, 30, View from above: -90, 10, 90
        fig = plt.figure(figsize=(100,100))
        ax = fig.add_subplot(111, projection='3d')
        ax.azim = azim
        ax.dist = dist
        ax.elev = elev
        ax.set_axis_off()

        kwant.plot(self.system, site_size = 0.30, site_color=site_color, site_edgecolor = site_color, \
                   hop_lw = 0.0, hop_color = 'w', ax = ax,num_lead_cells = 10, lead_color='r', \
                   lead_site_edgecolor = 'r');


        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])

        xs, ys = [], []
        for coords in self.vertices:
            x, y = coords
            xs.append(x)
            ys.append(y)    
        ax.plot(xs,ys, lw = 10)
        
        if plot_subregions:
            for vertices in self.subregions_vertices:
                xs, ys = [], []
                for coords in vertices:
                    x, y = coords
                    xs.append(x)
                    ys.append(y) 
                ax.plot(xs,ys, lw = 5)
            
        plt.tight_layout(pad=0)
        if plot_fname is not None:
            plt.savefig(plot_fname, format="png")
            if show_plot:
                plt.show()
            plt.close()
        else:
            plt.show()
            plt.close()
        
    #********************************* Dividing the sample into subregions ********************************#
    
    def break_sample(self, Nx, Ny, cutoff):
        
        self.cutoff = cutoff
        sites = list(self.system.sites())
        top_sites, bot_sites = [], []
        
        for site in sites:
            x,y,z = site.pos
            if z == 0:
                bot_sites.append(site)
            else:
                top_sites.append(site)

        subregions_vertices = []
        sites_in_subregions_bot, sites_in_subregions_top = [], []
        
        subregion_vector_1 = (self.vertices[1] - self.vertices[0]) / Nx
        subregion_vector_2 = (self.vertices[3] - self.vertices[0]) / Ny

        for j in range(Ny):
            for i in range(Nx):

                translation_temporal = self.vertices[0] + i * subregion_vector_1 + j * subregion_vector_2 

                subregion_vertices = [translation_temporal]

                for i, vector in enumerate([subregion_vector_1, subregion_vector_2, -subregion_vector_1, -subregion_vector_2]):
                    subregion_vertices.append(subregion_vertices[i] + vector)

                subregions_vertices.append(subregion_vertices)
                subregion_polygon = Polygon(subregion_vertices)

                sites_in_subregion_bot = []
                sites_in_subregion_top = []

                for site in sites:
                    x,y,z = site.pos
                    point = Point([x,y])

                    if subregion_polygon.distance(point) > cutoff:
                        continue

                    if z == 0:
                        sites_in_subregion_bot.append(site)
                    else:
                        sites_in_subregion_top.append(site)

                sites_in_subregions_bot.append(sites_in_subregion_bot)
                sites_in_subregions_top.append(sites_in_subregion_top)
                
        self.subregions_vertices = subregions_vertices
        self.sites_in_subregions_bot = sites_in_subregions_bot
        self.sites_in_subregions_top = sites_in_subregions_top
        
    #**************************************** Add disorder domains ****************************************#
        
    def add_domains_polygons(self, domains_polygons_fname, polygons_ensemble_index):
        
        data = np.load(domains_polygons_fname, allow_pickle = True)
        polygons = list(data['polygons'][polygons_ensemble_index])
        polygons.reverse()
        self.domains_polygons = polygons #data['polygons'][polygons_ensemble_index]
        self.scaling_factors = [data['sample_length'] / self.length, data['sample_width'] / self.width]
        
    @staticmethod
    def distance(site1, site2, plane_projection = False): 

        x1,y1,z1 = site1.pos
        x2,y2,z2 = site2.pos
        if plane_projection:
            return(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))
        return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2-z1) ** 2)
        
    #*************************** Calculate interlayer hopping between two sites ***************************#
    
    def interlayer_hopping(self, site1, site2):

        dist = self.distance(site1, site2)
        ex = np.exp(- (dist - d0) / lambda0)

        site1_in_some_domain = False
        site2_in_some_domain = False

        for i, domain in enumerate(self.domains_polygons):
            x,y,z = site1.pos
            x_post, y_post = self.transform_coords([[x, y]])[0]
            point = Point([x_post,y_post])
            if point.within(domain):
                site1_in_some_domain = True
                break

        for j, domain in enumerate(self.domains_polygons):
            x,y,z = site2.pos
            x_post, y_post = self.transform_coords([[x, y]])[0]
            point = Point([x_post,y_post])
            if point.within(domain):
                site2_in_some_domain = True
                break

        if not site1_in_some_domain or not site1_in_some_domain:
            print('Warning, a node was found to be outside all domains!')
            return 0.

        Vpps_updated = 0.5 * (self.domains_hoppings[i] + self.domains_hoppings[j])

        return Vpps_updated * ex * d0 * d0 / (dist ** 2)
    
    #*********************************** Adding the intralayer hoppings ***********************************#
    
    def add_interlayer_hoppings(self):
        
        if self.domains_polygons is None:
            raise AttributeError('You have not assigned the disorder domain polygons to the sample!')
            
        self.domains_hoppings = []
        # Assign the interlayer hoppings to the disorder domains

        for i in range(len(self.domains_polygons) - 1):
            self.domains_hoppings.append(Vpps)

        # Assign the interlayer hopping to the residue domain (the background, ordered domain)
        self.domains_hoppings.append(Vpps) 
                
        for i, (sites_bot, sites_top) in enumerate(zip(self.sites_in_subregions_bot, self.sites_in_subregions_top)):
            for site1 in sites_bot:
                for site2 in sites_top:
                    dist = self.distance(site1, site2, plane_projection = True)
                    if dist > self.cutoff:
                        continue
                    self.system[site1,site2] = lambda site1, site2: self.interlayer_hopping(site1, site2)
                    
    #****************************************** Finalize system ******************************************#
    
    def finalize_system(self):
        self.system = self.system.finalized()
        
        
