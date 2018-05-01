from . import constants
#import constants
from . import regex
#import regex
import re
import math
import numpy as np
from . import geometry_transform_helper as gth 
#import geometry_transform_helper as gth
import collections

"""
Contains Atom and Molecule classes for reading, saving and editing the geometry of a molecule 
Built around reading internal coordinates 
"""

class Atom(object):
    """
    The Atom class holds information about the geometry of an atom
        Parameters
        ----------
        label : str
            The atomic symbol
        r_idx  : str
            The bond connectivity index, as represented in a Z-matrix
        a_idx  : str
            The angle connectivity index, as represented in a Z-matrix
        d_idx  : str
            The dihedral connectivity index, as represented in a Z-matrix
        intcoords  : dict
            A dictionary of geometry parameter labels (e.g. "R1") and the value for this atom
    """
    def __init__(self, label, r_idx=None, a_idx=None, d_idx=None, intcoords=collections.OrderedDict()):
        self.label = label
        self.r_idx = r_idx
        self.a_idx = a_idx
        self.d_idx = d_idx
        self.intcoords = intcoords
        self.update_intcoords
        self.coords = np.array([None, None, None]) 
    
    def update_intcoords(self):
        self.geom_vals = list(self.intcoords.values())
        while len(self.geom_vals) < 3:
            self.geom_vals.append(None)
        self.rval = self.geom_vals[0]
        self.aval = self.geom_vals[1]
        self.dval = self.geom_vals[2]

    
# This framework is likely temporary. 
# It is probably better to let github/mcocdawc/chemcoord handle internals and cartesians in the future.
class Molecule(object):
    """
    The Molecule class holds geometry information about all the atoms in the molecule
    Requires initialization with a file string containing internal coordinates
    """
    def __init__(self, zmat_string):
        self.zmat_string = zmat_string
        self.extract_zmat(self.zmat_string)
         
    
    def extract_zmat(self, zmat_string):
        """
        This should maybe just be in the init method.
        Take the string which contains an isolated Z matrix definition block,
        and extract information and save the following attributes:
        self.n_atoms         - the number of atoms in the molecule
        self.atom_labels     - a list of element labels 'H', 'O', etc.
        self.geom_parameters - a list of geometry labels 'R3', 'A2', etc.
        self.atoms           - a list of Atom objects containing complete Z matrix information for each Atom
        """
        # grab array like representation of zmatrix and count the number of atoms 
        zmat_array = [line.split() for line in zmat_string.splitlines() if line]
        self.n_atoms = len(zmat_array)

        # find geometry parameter labels 
        # atom labels will always be at index 0, 1, 3, 6, 6++4... 
        # and geometry parameters are all other matches
        tmp = re.findall(regex.coord_label, zmat_string)
        self.atom_labels = []
        for i, s in enumerate(tmp):
                if (i == 0) or (i == 1) or (i == 3):
                    self.atom_labels.append(tmp[i])
                if ((i >= 6) and ((i-6) % 4 == 0)):
                    self.atom_labels.append(tmp[i])
        self.geom_parameters = [x for x in tmp if x not in self.atom_labels]
        
        self.atoms = []
        for i in range(self.n_atoms):
            label = zmat_array[i][0]
            intcoords = collections.OrderedDict()
            r_idx, a_idx, d_idx = None, None, None
            if (i >= 1):
                r_idx = int(zmat_array[i][1]) - 1
                intcoords[zmat_array[i][2]] = None
            if (i >= 2):
                a_idx = int(zmat_array[i][3]) - 1
                intcoords[zmat_array[i][4]] = None
            if (i >= 3):
                d_idx = int(zmat_array[i][5]) - 1
                intcoords[zmat_array[i][6]] = None
            self.atoms.append(Atom(label, r_idx, a_idx, d_idx, intcoords))
    
    def update_intcoords(self, disp):
        """
        Disp is a dictionary of geometry parameters and their new values, in angstrom and degrees
        {'R1': 1.01, 'R2':2.01, 'A1':104.5 ...}
        """
        for key in disp:
            for atom in self.atoms:
                if key in atom.intcoords:
                    atom.intcoords[key] = disp[key]
        # update Atom variables since intcoords maybe was changed, some redundancy here
        for atom in self.atoms:
            atom.update_intcoords()

    def zmat2xyz(self):
        """
        Converts Z-matrix representation to cartesian coordinates
        Perserves the element ordering of the Z-matrix
        Assumes Z-matrix is using degrees
        """
        if (self.n_atoms >= 1):
            self.atoms[0].coords = np.array([0.0, 0.0, 0.0])
        if (self.n_atoms >= 2):
            self.atoms[1].coords = np.array([0.0, 0.0, self.atoms[1].rval])
        if (self.n_atoms >= 3):
            r1,  r2  = self.atoms[1].rval, self.atoms[2].rval
            rn1, rn2 = self.atoms[1].r_idx, self.atoms[2].r_idx
            a1 = self.atoms[2].aval * constants.deg2rad 
            y = r2*math.sin(a1)
            z = self.atoms[rn2].coords[2] + (1-2*float(rn2==1))*r2*math.cos(a1)
            self.atoms[2].coords = np.array([0.0, y, z])
        for i in range(3, self.n_atoms):
            atom = self.atoms[i]
            coords1 = self.atoms[atom.r_idx].coords
            coords2 = self.atoms[atom.a_idx].coords
            coords3 = self.atoms[atom.d_idx].coords
            self.atoms[i].local_axes = gth.get_local_axes(coords1, coords2, coords3)
            #here
            bond_vector = gth.get_bond_vector(atom.rval, atom.aval * constants.deg2rad, atom.dval * constants.deg2rad)
            disp_vector = np.array(np.dot(bond_vector, self.atoms[i].local_axes))
            for p in range(3):
                atom.coords[p] = self.atoms[atom.r_idx].coords[p] + disp_vector[p]

        cartesian_coordinates = []
        for atom in self.atoms:
            cartesian_coordinates.append(atom.coords)
        return np.array(cartesian_coordinates)

 