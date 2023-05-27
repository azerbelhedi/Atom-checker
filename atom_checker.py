import numpy as np
import subprocess
import os
import sys
from pymatgen.io.cif import CifWriter
from pymatgen.io.vasp.inputs import Poscar

null_device = open(os.devnull, 'w')

def getAtoms(vaspFile):
    with open(vaspFile, 'r') as f:
        # Skip the header lines
        for i in range(6):
            f.readline()

        # Read the number of atoms assumes C then Na
        atomsNbString = f.readline().strip()
        # print(atomsNbString)

        nbC = int(atomsNbString.split(' ')[0])
        nbNa = int(atomsNbString.split(' ')[2])

        # Skip the 'Cartesian' line5
        f.readline()

        # Initialize an empty array to store the atom positions
        positionsNa = np.zeros((nbNa, 3))
        positionsC = np.zeros((nbC, 3))

        for i in range(nbC):
            line = f.readline().strip().split()
            position = np.array(
                [float(line[0]), float(line[1]), float(line[2])])
            # print(position)
            positionsC[i] = position

        for i in range(nbNa):
            line = f.readline().strip().split()
            # print(line)
            position = np.array(
                [float(line[0]), float(line[1]), float(line[2])])
            # print(position)
            positionsNa[i] = position

    # Return the positions of the Na atoms
    return positionsC[positionsC.any(axis=1)], positionsNa[positionsNa.any(axis=1)], nbC, nbNa


def runVmd(originalPostionVector, periodicPositionVector, atomId, cifPath, logPath):
    # create tcl file from template.tcl with xyzPosition, atomId and cifFile
    originalPositionString = "{" + ' '.join(str(x) for x in originalPostionVector) + "}"
    periodicPositionString = "{" + ' '.join(str(x) for x in periodicPositionVector) + "}"
    
    print("current Na atom in display:")
    print(f"index: {atomId}")
    print(f"position (original from .vasp): {originalPositionString}")
    print(f"position (in periodic lattice from .cif) {periodicPositionString}")
    
    file = open(logPath, "a")
    
    file.write("current Na atom in display:\n")
    file.write(f"index: {atomId}\n")
    file.write(f"position (original from .vasp): {originalPositionString}\n")
    file.write(f"position (in periodic lattice from .cif) {periodicPositionString}\n")
    
    createTclFile(cifPath, periodicPositionString)
    
    vmd_args = ["vmd", "-e", "auto_script.tcl"]
    proc = subprocess.Popen(vmd_args, stdout=null_device, stderr=null_device)
        
    decision = ""
    while(decision != "delete" and decision != "keep"):
        decision = input(f"delete/keep Na atom nb {atomId}? ")
    
    # Save decision to log (logPath, atom id, atom position and decision)
    print(f"saving decision: {decision}\n")
    file.write(f"decision: {decision}\n\n")
    file.close()
    proc.terminate()


def createTclFile(cifFilePath, positionsString):
    with open("template.tcl", 'r') as src, open("auto_script.tcl", 'w') as dest:

        dest.write("# auto-generated script part start\n")
        dest.write(f'set filename "{cifFilePath}"\n')
        dest.write(f'set new_atom_position {positionsString}\n')
        dest.write("# auto-generated script part end\n\n")

        for line in src:
            dest.write(line)


def checkAtoms(folderName):
    print(f'reading data from "{folderName}" folder.')
    
    basePath = f"compact/{folderName}/{folderName}"
    vaspPath = basePath + ".vasp"
    cifPath = basePath + ".cif"
    newCifPath = basePath + "-auto.cif"
    logPath = f"log/{folderName}.log"

    print(f'cif file path: {cifPath}')
    print(f'vasp file path: {vaspPath}')
    
    # load original positions of sodium atoms from .vasp file
    originalCPositions, originalNaPositions, nbCarbon, nbSodium  = getAtoms(vaspPath)
    print(f"sodium atoms nb: {len(originalNaPositions)}\n")
    
    print(f'{nbCarbon} ({len(originalCPositions)}) carbon atoms and {nbSodium} ({len(originalNaPositions)}) sodium atoms')
    
    poscar = Poscar.from_file(vaspPath)
    lattice = poscar.structure.lattice.matrix

    carbonAtoms = poscar.structure[:nbCarbon]
    carbonStructure = poscar.structure.from_sites(carbonAtoms)
    
    naAtoms = poscar.structure[nbCarbon: nbCarbon + nbSodium]
    naStructure = poscar.structure.from_sites(naAtoms)
    
    naPositions = np.array([atom.frac_coords for atom in naStructure])
    
    # Apply periodic lattice to positions
    naPositions = np.mod(naPositions, 1.0)
    naPositions = np.dot(naPositions, lattice)
        
    cif_writer = CifWriter(carbonStructure)
    cif_writer.write_file(newCifPath)
     
    for index, originalPosition in enumerate(originalNaPositions):
        runVmd(originalPosition, naPositions[index], index, newCifPath, logPath)
   
def main():
    if len(sys.argv) == 1:
        print('you have to provide the name of the structure (e.g. BEA or BEB etc)')
    else:
        checkAtoms(sys.argv[1])


main()