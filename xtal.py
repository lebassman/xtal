"""xtal is an umbrella package for various tools used to manipulate atomic trajectories"""
import copy
import numpy as np
import progressbar

class AtTraj(object):

    def __init__(self):
        self.snaplist = list()
        self.box = np.ndarray([3, 3])
        self.abc = np.ndarray([1, 3])
        self.ang = np.ndarray([1, 3])
        self.description = ""
        self.mat_dir_to_car = np.zeros([3, 3])
        self.mat_car_to_dir = np.zeros([3, 3])
        self.boxvolume = 0.0
        print 'Atomic trajectory initialized'

    def create_snapshot(self, snapshot):
        """Append a new snapshot to the snapshot list"""
        newsnapshot = snapshot(self)
        self.snaplist.append(newsnapshot)
        return newsnapshot

    def dirtocar(self):
        """Convert all atoms in trajectory to cartesian coordinates"""
        for snapshot in self.snaplist:
            snapshot.dirtocar()

    def cartodir(self):
        """Convert all atoms in trajectory to fractional coordinates"""
        for snapshot in self.snaplist:
            snapshot.cartodir()

    def remap_id(self, old_id, new_id):
        """Rewrite all atom old_id in trajectory to new_id"""
        for snapshot in self.snaplist:
            for atom in snapshot.atomlist:
                atom.remap_id(old_id, new_id)

    def vectortocar(self, inputvec):
        """Convert any vector from fractional units to cartesian"""
        return np.inner(self.mat_dir_to_car, inputvec)

    def vectortodir(self, inputvec):
        """Convert any vector from cartesian units to fractional units"""
        return np.inner(self.mat_car_to_dir, inputvec)

    def move(self, vector):
        """Move all atoms in the trajectory by given cartesian vector"""
        for snapshot in self.snaplist:
            snapshot.move(vector)

    def inbox(self):
        """Fold all atoms in trajectory to lie within the simulation cell assuming PBC"""
        for snapshot in self.snaplist:
            snapshot.inbox()

    def rotate(self, center, angle):
        """Rotate all atoms in the trajectory by given angle about given center"""
        for snapshot in self.snaplist:
            snapshot.rotate(center, angle)


    def make_periodic(self, num_of_images):
        """Create periodic images all snapshots of current simulation cell"""
        newprogressbar = progressbar.ProgressBar()
        for snapshot in newprogressbar(self.snaplist):
            snapshot.make_periodic(num_of_images)

        # Adjust the box sizes and recompile transformation matrices
        self.box[0, :] = self.box[0, :] * num_of_images[0]
        self.box[1, :] = self.box[1, :] * num_of_images[1]
        self.box[2, :] = self.box[2, :] * num_of_images[2]
        self.make_dircar_matrices()
        self.dirtocar()



    # def read_snapshot_lammps(self, filename):
    #     lammps_snapfile = open(filename, "r")
    #     lammps_snapfile.readline() # Comment line for Timestep
    #     self.stepcount = int(lammps_snapfile.readline().strip())

    #     lammps_snapfile.readline() # Comment line for Atom Count
    #     atomcount = int(lammps_snapfile.readline().strip())

    #     lammps_snapfile.readline() # Comment line for box bounds
    #     xlo_bound, xhi_bound, xy = map(float, lammps_snapfile.readline().split())
    #     ylo_bound, yhi_bound, xz = map(float, lammps_snapfile.readline().split())
    #     zlo_bound, zhi_bound, yz = map(float, lammps_snapfile.readline().split())

    #     xlo = xlo_bound - min(0.0, xy, xz, xy+xz)
    #     xhi = xhi_bound - max(0.0, xy, xz, xy+xz)
    #     ylo = ylo_bound - min(0.0, yz)
    #     yhi = yhi_bound - max(0.0, yz)
    #     zlo = zlo_bound
    #     zhi = zhi_bound

    #     self.box[0, :] = [xhi-xlo, 0.0, 0.0]
    #     self.box[1, :] = [xy, yhi-ylo, 0.0]
    #     self.box[2, :] = [xz, yz, zhi-zlo]

    #     self.make_dircar_matrices() # Uniform representation of box dimensions

    #     lammps_snapfile.readline() # Comment line for Atom positions
    #     for thisatomcount in range(0, atomcount):
    #         basisline = lammps_snapfile.readline()
    #         myatom = Atom()
    #         myatom.element, myatom.cart = [basisline.split()[0],
    #                                        np.array(map(float, basisline.split()[1:4]))]
    #         self.atomlist.append(myatom)
    #     self.cartodir()

    #     lammps_snapfile.close()


    def read_snapshot_vasp(self, filename):
        """Read new VASP snapshot from file and append to current trajectory"""
        snapshot = self.create_snapshot(Snapshot)

        vasp_snapfile = open(filename, "r")

        self.description = vasp_snapfile.readline().strip()
        mymultiplier = float(vasp_snapfile.readline())

        self.box[0, :] = map(float, vasp_snapfile.readline().split())
        self.box[1, :] = map(float, vasp_snapfile.readline().split())
        self.box[2, :] = map(float, vasp_snapfile.readline().split())
        self.box = self.box * mymultiplier

        self.make_dircar_matrices() # Uniform representation of box dimensions from POSCAR file

        basisline = vasp_snapfile.readline()
        atarray = basisline.split()

        basisline = vasp_snapfile.readline()
        atoms_of_type = map(int, basisline.split())

        isindirectcoords = vasp_snapfile.readline().lower().strip()[0] == 'd' # Check Dir. or Cart.

        if isindirectcoords:
            for index, numbers in enumerate(atoms_of_type):
                for thistype in range(0, numbers):  # dummy counter #pylint: disable=unused-variable
                    basisline = vasp_snapfile.readline()
                    myatom = snapshot.create_atom(Atom)
                    myatom.fract = np.array(map(float, basisline.split()))
                    myatom.element = atarray[index].upper()
            self.dirtocar() # Populate cartesian values from fractional coordinates for each atom
        else:
            for index, numbers in enumerate(atoms_of_type):
                for thistype in range(0, numbers):
                    basisline = vasp_snapfile.readline()
                    myatom = snapshot.create_atom(Atom)
                    myatom.cart = np.array(map(float, basisline.split()))
                    myatom.element = atarray[index].upper()
            self.cartodir() # Populate fractional coordinates from cartesian values of each atom

        vasp_snapfile.close()



    def read_trajectory_pwp(self, directory):
        """Read new trajectory from PWP data directory"""
        bohr_to_angstrom = 0.52917724900001
        boxfilename = directory+"/qm_box.d"
        pwp_boxfile = open(boxfilename, "r")
        # Remove first two lines
        pwp_boxfile.readline()
        pwp_boxfile.readline()
        currline = map(float, pwp_boxfile.readline().split())
        a = currline[1]*bohr_to_angstrom # pylint: disable=invalid-name
        b = currline[2]*bohr_to_angstrom # pylint: disable=invalid-name
        c = currline[3]*bohr_to_angstrom # pylint: disable=invalid-name
        alpha = currline[4]*np.pi/180.0
        beta = currline[5]*np.pi/180.0
        gamma = currline[6]*np.pi/180.0
        self.abc = np.array([a, b, c])
        self.ang = np.array([alpha, beta, gamma])
        pwp_boxfile.close()
        self.abc_to_box()

        posfilename = directory+"/qm_ion.d"
        pwp_posfile = open(posfilename, "r")
        # Remove first comment line
        pwp_posfile.readline()


        while True:
            firstline = pwp_posfile.readline()

            if firstline == '':
                break

            thissnapshot = self.create_snapshot(Snapshot)

            header = map(int, firstline.split())
            numelements = header[1]

            numatoms_per_element = list()

            for element in range(0, numelements):
                numatoms_per_element.append(header[element+2])

            numatoms = sum(numatoms_per_element)

            numlines = int(np.ceil(numatoms/3.0))

            multiplier = map(float, pwp_posfile.readline().split())

            for line in range(0, numlines):
                thisline = map(float, pwp_posfile.readline().split())
                for index in range(0, 3):
                    if numatoms >= ((line*3)+index+1):
                        thisatom = thissnapshot.create_atom(Atom)
                        thisatom.fract = np.array([thisline[(index*3)+0],
                                                   thisline[(index*3)+1],
                                                   thisline[(index*3)+2]])
                        thisatom.fract = thisatom.fract * multiplier

            atomindex = 0
            for element in range(0, numelements):
                for atom in range(0, numatoms_per_element[element]): # pylint: disable=unused-variable
                    thissnapshot.atomlist[atomindex].element = 'UE'+str(element)
                    atomindex += 1


    def abc_to_box(self):
        """Convert cell lengths (a, b, c) and angles (alpha, beta, gamma) into box vectors"""
        a = self.abc[0] # pylint: disable=invalid-name
        b = self.abc[1] # pylint: disable=invalid-name
        c = self.abc[2] # pylint: disable=invalid-name
        alpha = self.ang[0]
        beta = self.ang[1]
        gamma = self.ang[2]
        box = np.ndarray([3, 3])
        box[0, :] = [a,
                     0.0,
                     0.0]

        box[1, :] = [b*np.cos(gamma),
                     b*np.sin(gamma),
                     0.0]

        box[2, :] = [c*np.cos(beta),
                     c*np.cos(alpha)*np.sin(gamma),
                     c*np.sqrt(1 - (np.cos(beta)*np.cos(beta))
                               - (np.cos(alpha)*np.sin(gamma)*np.cos(alpha)*np.sin(gamma)))]
        self.box = box


    def box_to_abc(self):
        """Convert box vectors into cell lengths (a, b, c) and angles (alpha, beta, gamma)"""
        a = np.linalg.norm(self.box[0, :]) # pylint: disable=invalid-name
        b = np.linalg.norm(self.box[1, :]) # pylint: disable=invalid-name
        c = np.linalg.norm(self.box[2, :]) # pylint: disable=invalid-name
        alpha = np.arccos(np.inner(self.box[1, :], self.box[2, :])/(b*c))
        beta = np.arccos(np.inner(self.box[2, :], self.box[0, :])/(c*a))
        gamma = np.arccos(np.inner(self.box[0, :], self.box[1, :])/(a*b))
        self.abc = np.array([a, b, c])
        self.ang = np.array([alpha, beta, gamma])


    def make_dircar_matrices(self):
        """Construct matrices to convert between direct and cartesian coordinates"""
        a = np.linalg.norm(self.box[0, :]) # pylint: disable=invalid-name
        b = np.linalg.norm(self.box[1, :]) # pylint: disable=invalid-name
        c = np.linalg.norm(self.box[2, :]) # pylint: disable=invalid-name
        alpha = np.arccos(np.inner(self.box[1, :], self.box[2, :])/(b*c))
        beta = np.arccos(np.inner(self.box[2, :], self.box[0, :])/(c*a))
        gamma = np.arccos(np.inner(self.box[0, :], self.box[1, :])/(a*b))

        self.boxvolume = np.inner(self.box[0, :], np.cross(self.box[1, :], self.box[2, :]))

        self.mat_dir_to_car[0, :] = [a,
                                     b * np.cos(gamma),
                                     c * np.cos(beta)]

        self.mat_dir_to_car[1, :] = [0,
                                     b*np.sin(gamma),
                                     c*((np.cos(alpha)-(np.cos(beta)*np.cos(gamma)))/np.sin(gamma))]

        self.mat_dir_to_car[2, :] = [0,
                                     0,
                                     self.boxvolume / (a * b * np.sin(gamma))]

        self.mat_car_to_dir[0, :] = [1.0/a,
                                     0.0 - (np.cos(gamma)/(a * np.sin(gamma))),
                                     b * c * ((np.cos(alpha)*np.cos(gamma))
                                              - np.cos(beta))/(self.boxvolume * np.sin(gamma))]

        self.mat_car_to_dir[1, :] = [0.0,
                                     1.0 / (b * np.sin(gamma)),
                                     a * c * ((np.cos(beta)*np.cos(gamma))
                                              - np.cos(alpha))/(self.boxvolume * np.sin(gamma))]

        self.mat_car_to_dir[2, :] = [0.0,
                                     0.0,
                                     a * b * np.sin(gamma) / self.boxvolume]



    def sort_by_element(self):
        """Sort all snapshots in the trajectory by element"""
        for snapshot in self.snaplist:
            snapshot.atomlist.sort_by_element()



    def identical_sort(self, refsnap, opsnap, usePBC=True):
        """Copy atom sort order from one snapshot to another - uses PBC"""
        for refindex, refatom in enumerate(refsnap.atomlist):
            mindist = max(np.linalg.norm(self.abc), 1.0)
            for opindex in range(refindex, len(opsnap.atomlist)):
                if usePBC:
                    currdist = opsnap.pbc_distance(opsnap.atomlist[opindex], refatom)
                else:
                    currdist = np.linalg.norm(opsnap.atomlist[opindex].fract - refatom.fract)

                if currdist <= mindist:
                    swapindex = opindex
                    mindist = currdist

            opsnap.atomlist[swapindex], opsnap.atomlist[refindex] \
                = opsnap.atomlist[refindex], opsnap.atomlist[swapindex]



#--------------------------------------------------

class Snapshot(AtTraj):
    description = ""

    def __init__(self, trajectory):
        self.trajectory = trajectory
        self.atomlist = list()

    def create_atom(self, atom):
        """Create a new Atom instance and append to current snapshot"""
        newatom = atom(self)
        self.atomlist.append(newatom)
        return newatom

    def dirtocar(self):
        """Convert all atoms in snapshot to cartesian coordinates"""
        for atom in self.atomlist:
            atom.dirtocar()

    def cartodir(self):
        """Convert all atoms in snapshot to fractional coordinates"""
        for atom in self.atomlist:
            atom.cartodir()

    def rotate(self, center, angle):
        """Rotate all atoms in the snapshot by given angle about given center"""
        for atom in self.atomlist:
            atom.rotate(center, angle)

    def move(self, vector):
        """Move all atoms in the snapshot by given cartesian vector"""
        for atom in self.atomlist:
            atom.move(vector)

    def make_periodic(self, num_of_images):
        """Create periodic images of the current snapshot of current simulation cell"""
        original_atomlist = list(self.atomlist)
        # Clear the original list
        self.atomlist = []
        # Loop over z, y and x respectively
        for zimage in range(0, num_of_images[2]):
            for yimage in range(0, num_of_images[1]):
                for ximage in range(0, num_of_images[0]):
                    for singleatom in original_atomlist:
                        newatom = copy.copy(singleatom)
                        newatom.fract = newatom.fract + np.array([ximage, yimage, zimage])
                        newatom.fract = np.divide(newatom.fract, num_of_images)
                        self.atomlist.append(newatom)

        # Cleanup
        del original_atomlist[:]


    def sort_by_element(self):
        self.atomlist.sort(key=lambda x: x.element)


    def inbox(self):
        """Fold all atoms in Snapshot to lie within the simulation cell assuming PBC"""
        for atom in self.atomlist:
            atom.inbox()

    def write_snapshot_vasp(self, filename, write_in_direct):
        """Write out positions of atoms in the current snapshot in the VASP POSCAR format"""
        vasp_snapfile = open(filename, "w")
        vasp_snapfile.write(self.trajectory.description+'\n')
        vasp_snapfile.write('1.000000\n') # Default multiplier for all VASP files
        np.savetxt(vasp_snapfile, self.trajectory.box, fmt='%19.16f', delimiter="   ", newline="\n")

        # Sort atoms by element before counting number of atoms by element
        self.atomlist.sort(key=lambda x: x.element)
        uniquesdict = {}
        for singleatom in self.atomlist:
            uniquesdict[singleatom.element] = singleatom.element
        uniqueslist = uniquesdict.values()

        uniquesdict = {}
        uniquesdict1 = {}
        for uniqueelement in uniqueslist:
            uniquesdict[uniqueelement] = str(len([p for p in self.atomlist \
                                                  if p.element == uniqueelement]))
            uniquesdict1[uniqueelement] = uniqueelement
        uniqueslist = uniquesdict.values()
        uniqueslist1 = uniquesdict1.values()

        vasp_snapfile.write("  ".join(uniqueslist1).title()+'\n')
        vasp_snapfile.write("  ".join(uniqueslist)+'\n')

        if write_in_direct:
            vasp_snapfile.write('Direct\n')
            for uniqueelement in uniqueslist1:
                subsetofatomlist = (atoms for atoms in self.atomlist \
                                    if atoms.element == uniqueelement)
                for singleatom in subsetofatomlist:
                    np.savetxt(vasp_snapfile, singleatom.fract[None],
                               fmt='%19.16f', delimiter="   ", newline="\n ")
        else:
            vasp_snapfile.write('Cartesian\n')
            for uniqueelement in uniqueslist1:
                subsetofatomlist = (atoms for atoms in self.atomlist
                                    if atoms.element == uniqueelement)
                for singleatom in subsetofatomlist:
                    np.savetxt(vasp_snapfile, singleatom.cart[None],
                               fmt='%19.16f', delimiter="   ", newline="\n ")


        vasp_snapfile.close()



    def remove_overlap(self, cutoff):
        """Remove one of a pair of atoms that are within <cutoff> distance of each other
        <cutoff> is given in Angstroms

        Atomlist is sorted according to x- y- and z- positions
        Loop through the atomlist to find out if atom i and i+1 are within cutoff.
        If yes, remove atom i from the atomlist
        Loop until you don't find any neighbors within the cutoff"""

        num_of_initial_atoms = len(self.atomlist)
        num_of_removed_atoms = 0

        found_duplicate_atom = True

        while found_duplicate_atom:
            found_duplicate_atom = False

            self.atomlist.sort(key=lambda x: int(x.cart[0]))
            self.atomlist.sort(key=lambda x: int(x.cart[1]))
            self.atomlist.sort(key=lambda x: int(x.cart[2]))
            for index, atom in enumerate(self.atomlist): # pylint: disable=unused-variable
                if index < len(self.atomlist)-1: # Don't want last item, must compare index, index+1
                    if self.pbc_distance(self.atomlist[index], self.atomlist[index+1]) < cutoff:
                        del self.atomlist[index]
                        num_of_removed_atoms += 1
                        found_duplicate_atom = True

            self.atomlist.sort(key=lambda x: int(x.cart[1]))
            self.atomlist.sort(key=lambda x: int(x.cart[2]))
            self.atomlist.sort(key=lambda x: int(x.cart[0]))
            for index, atom in enumerate(self.atomlist):
                if index < len(self.atomlist)-1: # Don't want last item, must compare index, index+1
                    if self.pbc_distance(self.atomlist[index], self.atomlist[index+1]) < cutoff:
                        del self.atomlist[index]
                        num_of_removed_atoms += 1
                        found_duplicate_atom = True

            self.atomlist.sort(key=lambda x: int(x.cart[2]))
            self.atomlist.sort(key=lambda x: int(x.cart[0]))
            self.atomlist.sort(key=lambda x: int(x.cart[1]))
            for index, atom in enumerate(self.atomlist):
                if index < len(self.atomlist)-1: # Don't want last item, must compare index, index+1
                    if self.pbc_distance(self.atomlist[index], self.atomlist[index+1]) < cutoff:
                        del self.atomlist[index]
                        num_of_removed_atoms += 1
                        found_duplicate_atom = True

        if not found_duplicate_atom:
            print 'No duplicate atoms found.'
        else:
            print num_of_removed_atoms, 'atoms removed. Atomlist size reduced from', \
                  num_of_initial_atoms, 'to', len(self.atomlist)


    def pbc_distance(self, atom1, atom2):
        """Calculate minimum distance between two atoms assuming PBC"""
        atom1.fract = atom1.fract - np.floor(atom2.fract)
        atom2.fract = atom2.fract - np.floor(atom2.fract)
        diff0 = atom2.fract - atom1.fract
        diff1 = diff0 + 1
        diff2 = diff0 - 1
        diff0 = np.append([diff0], [diff1], axis=0)
        diff0 = np.append(diff0, [diff2], axis=0)
        diff = []
        diff.append(sorted(diff0[:, 0], key=abs)[0])
        diff.append(sorted(diff0[:, 1], key=abs)[0])
        diff.append(sorted(diff0[:, 2], key=abs)[0])
        mindist_fract_vec = np.array(diff)
        mindist_cart_vec = np.dot(np.matrix.transpose(self.trajectory.box), mindist_fract_vec)
        mindist = np.linalg.norm(mindist_cart_vec)
        return mindist


#--------------------------------------------------


class Atom(Snapshot):

    def __init__(self, snapshot):
        self.snapshot = snapshot

    element = ""
    fract = np.ndarray((1, 3))
    cart = np.ndarray((1, 3))

    def dirtocar(self):
        """Convert current atom to cartesian coordinates"""
        self.cart = np.array(np.inner(self.snapshot.trajectory.mat_dir_to_car, self.fract))

    def cartodir(self):
        """Convert current atom to fractional coordinates"""
        self.fract = np.array(np.inner(self.snapshot.trajectory.mat_car_to_dir, self.cart))

    def move(self, vector):
        """Move current atom by given cartesian vector"""
        self.cart = self.cart + vector

    def remap_id(self, old_id, new_id):
        """Rewrite atom old_id to new_id"""
        if self.element == old_id:
            self.element = new_id

    def rotate(self, center, angle):
        """Rotate current atom by given angle about given center"""
        initpos = self.cart[[0, 1]]
        recenter = initpos - center
        rotmat = np.array([[np.cos(angle), 0.0-np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        rotated = rotmat.dot(recenter)
        finalpos = rotated + center
        self.cart[0] = finalpos[0]
        self.cart[1] = finalpos[1]

    def inbox(self):
        """Fold atom position to lie within the simulation cell assuming PBC"""
        self.fract = self.fract - np.floor(self.fract)
        self.dirtocar()


#--------------------------------------------------



def is_sierpinski_carpet_filled(level, coords):
    """Calculate if the given fractional coordinates correspond to a filed pixel
    in the Sierpinksi carpet fractal of a given level

    Multiply the fractional coordinate with 3^n (for n = level..1) and check to see
    if it leaves a reminder of 1 upon division by 3 (i.e. it is the middle cell at any level)"""

    multiplier = 3**level

    x = int(coords[0]*multiplier) # pylint: disable=invalid-name
    y = int(coords[1]*multiplier) # pylint: disable=invalid-name

    while True:
        if x == 0 and y == 0:
            break

        if x%3 == 1 and y%3 == 1:
            return False

        x = int(x/3) # pylint: disable=invalid-name
        y = int(y/3) # pylint: disable=invalid-name

    return True
