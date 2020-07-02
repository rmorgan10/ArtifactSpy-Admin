# A module for collecting real images from the des machines
# Usage: python grab_real.py Real__20-07-02_15-33-17.tar.gz

import os
import sys

tarball = sys.argv[1]
des_path = '/home/s1/rmorgan/ArtifactSpyReal/TrainingSets/'
hep_path = '/afs/hep.wisc.edu/bechtol-group/ArtifactSpy/TrainingSets'

err_code = os.system('kinit rmorgan@FNAL.GOV')
if err_code != 0:
    sys.exit()

os.system('scp rmorgan@des50.fnal.gov:' + des_path + tarball + ' .')

err_code = os.system('kinit ramorgan2@HEP.WISC.EDU')
if err_code != 0:
    sys.exit()

os.system('scp ' + tarball + ' ramorgan2@login04.hep.wisc.edu:' + hep_path)

os.system('rm ' + tarball)
