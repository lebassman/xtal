import xtal
import numpy as np
import os

# Testing VASP integration
class TestVASP(object):

    def test_read_vasp_poscar_direct(self):
        """Test if VASP5 POSCARs in direct coordinates can be read"""
        u = xtal.AtTraj()
        u.read_snapshot_vasp('tests/POSCAR.VASP5.unitcell')
        assert len(u.snaplist[0].atomlist) == 3

    def test_read_vasp_poscar_cartesian(self):
        """Test if VASP5 POSCARs in cartesian coordinates can be read"""
        u = xtal.AtTraj()
        u.read_snapshot_vasp('tests/POSCAR.VASP5.cartesian.unitcell')
        assert len(u.snaplist[0].atomlist) == 3

    def test_make_periodic_vasp_poscar(self):
        """Test if VASP5 POSCARs an be PBC replicated"""
        u = xtal.AtTraj()
        u.read_snapshot_vasp('tests/POSCAR.VASP5.unitcell')
        u.make_periodic(np.array([5, 5, 3]))
        assert len(u.snaplist[0].atomlist) == 225

    def test_write_vasp_poscar_cartesian(self):
        """Test if VASP5 POSCARs can be written in cartesian coordinates"""
        u = xtal.AtTraj()
        u.read_snapshot_vasp('tests/POSCAR.VASP5.unitcell')
        u.snaplist[0].write_snapshot_vasp('tests/POSCAR',False)
        v = xtal.AtTraj()
        v.read_snapshot_vasp('tests/POSCAR')
        u_mo_atoms = [atom for atom in u.snaplist[0].atomlist if atom.element == "MO"]
        v_mo_atoms = [atom for atom in v.snaplist[0].atomlist if atom.element == "MO"]
        assert np.linalg.norm(u_mo_atoms[0].cart - v_mo_atoms[0].cart) < 0.0001
        os.remove('tests/POSCAR')

    def test_write_vasp_poscar_direct(self):
        """Test if VASP5 POSCARs can be written in fractional coordinates"""
        u = xtal.AtTraj()
        u.read_snapshot_vasp('tests/POSCAR.VASP5.cartesian.unitcell')
        u.snaplist[0].write_snapshot_vasp('tests/POSCAR',True)
        v = xtal.AtTraj()
        v.read_snapshot_vasp('tests/POSCAR')
        u_mo_atoms = [atom for atom in u.snaplist[0].atomlist if atom.element == "MO"]
        v_mo_atoms = [atom for atom in v.snaplist[0].atomlist if atom.element == "MO"]
        assert np.linalg.norm(u_mo_atoms[0].fract - v_mo_atoms[0].fract) < 0.0001
        os.remove('tests/POSCAR')



# Testing General trajectory methods
class TestGeneral(object):

    def test_remap_id(self):
        """Test if trajectory elements can be remapped"""
        u = xtal.AtTraj()
        u.read_snapshot_vasp('tests/POSCAR.VASP5.unitcell')
        u.remap_id('S','TE')
        no_S_atoms = len([atom for atom in u.snaplist[0].atomlist if atom.element == 'S'])
        no_Te_atoms = len([atom for atom in u.snaplist[0].atomlist if atom.element == 'TE'])
        assert (no_S_atoms, no_Te_atoms) == (0,2)

    def test_pbc_distance(self):
        """Test if distances between atoms are calculated correctly"""
        u = xtal.AtTraj()
        u.read_snapshot_vasp('tests/POSCAR.VASP5.unitcell')
        mo_atom = u.snaplist[0].atomlist[0]
        s_atom = u.snaplist[0].atomlist[1]
        same_atom_distance = u.snaplist[0].pbc_distance(mo_atom,mo_atom)
        different_atom_distance = u.snaplist[0].pbc_distance(mo_atom,s_atom)
        assert (same_atom_distance == 0.0 and different_atom_distance > 2.40 and different_atom_distance < 2.41)

    def test_dirtocar(self):
        """Test if fractional units can be converted to cartesian coordinates"""
        u = xtal.AtTraj()
        u.read_snapshot_vasp('tests/POSCAR.VASP5.unitcell')
        u.dirtocar()
        zpos_atom_one = u.snaplist[0].atomlist[0].cart[2]
        assert (zpos_atom_one > 3.0 and zpos_atom_one < 3.1)

    def test_remove_overlap(self):
        """Test if overlapping atoms are removed based on provided cutoff"""
        u = xtal.AtTraj()
        u.read_snapshot_vasp('tests/POSCAR.VASP5.duplicates.unitcell')
        snapshot = u.snaplist[0]
        raw_num_atoms = len(snapshot.atomlist)

        # Remove all duplicate atoms closer than 0.11
        snapshot.remove_overlap(0.11)
        pt1_pass1_num_atoms = len(snapshot.atomlist)
        snapshot.remove_overlap(0.11) # second pass shold not change anything
        pt1_pass2_num_atoms = len(snapshot.atomlist)

        # Remove all duplicate atoms closer than 0.21
        snapshot.remove_overlap(0.21)
        pt2_pass1_num_atoms = len(snapshot.atomlist)
        snapshot.remove_overlap(0.21) # second pass shold not change anything
        pt2_pass2_num_atoms = len(snapshot.atomlist)

        # Remove all duplicate atoms closer than 0.31
        snapshot.remove_overlap(0.31)
        pt3_pass1_num_atoms = len(snapshot.atomlist)
        snapshot.remove_overlap(0.31) # second pass shold not change anything
        pt3_pass2_num_atoms = len(snapshot.atomlist)

        assert (raw_num_atoms, pt1_pass1_num_atoms, pt1_pass2_num_atoms, \
                pt2_pass1_num_atoms, pt2_pass2_num_atoms, \
                pt3_pass1_num_atoms, pt3_pass2_num_atoms) == (6, 5, 5, 4, 4, 3, 3)

    def test_move_atoms(self):
        """Test if overlapping atoms are removed based on provided cutoff"""
        u = xtal.AtTraj()
        u.read_snapshot_vasp('tests/POSCAR.VASP5.unitcell')
        u.dirtocar()
        snapshot = u.snaplist[0]
        mo_atom = [atom for atom in snapshot.atomlist if atom.element == "MO"][0]
        s_atom_top = [atom for atom in snapshot.atomlist if atom.fract[2] > 0.15][0]
        s_atom_bottom = [atom for atom in snapshot.atomlist if atom.fract[2] < 0.1][0]

        # Establish baselines
        top_dist = snapshot.pbc_distance(mo_atom,s_atom_top)
        bot_dist = snapshot.pbc_distance(mo_atom,s_atom_bottom)

        # Move the top and bottom S atoms by different distances. This should increase pbc_distances
        s_atom_top.move(np.array([0.0,0.0,5.0]))
        s_atom_bottom.move(np.array([0.0,0.0,-6.0]))
        u.cartodir()
        m1_top_dist = snapshot.pbc_distance(mo_atom,s_atom_top)
        m1_bot_dist = snapshot.pbc_distance(mo_atom,s_atom_bottom)

        # Move the entire snapshot. This should not change pbc_distances
        snapshot.move(np.array([0.0,0.0,9.0]))
        u.cartodir()
        m2_top_dist = snapshot.pbc_distance(mo_atom,s_atom_top)
        m2_bot_dist = snapshot.pbc_distance(mo_atom,s_atom_bottom)

        # Test all distances. Initially 2.4, Expands beyond 5.0. And then stays the same
        assert (top_dist < 2.41 and bot_dist < 2.41 and \
                m1_top_dist > 5.0 and m1_bot_dist > 6.0 and \
                np.isclose(m2_top_dist, m1_top_dist, atol=1e-5) and \
                np.isclose(m2_bot_dist, m1_bot_dist, atol=1e-5))
