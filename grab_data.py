# Grab data from DES Machines

import datetime
import glob
import numpy as np
import os
import random
import pandas as pd
import sys

timestamp = '{:%y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())
err_code = os.system('kinit rmorgan@FNAL.GOV')
if err_code != 0:
    sys.exit()

# Open a file
def open_dat(dat_file):
    infile = open(dat_file, 'r')
    lines = infile.readlines()
    infile.close()
    return lines

# Get phot data for single dat file
def get_terse_lc(lines):

    columns = [y for y in [x.split(' ') for x in lines if x[0:8] == 'VARLIST:'][0] if y != ''][1:-1]
    data = [[y for y in x.split(' ') if y != ''][1:-1] for x in lines if x[0:4] == 'OBS:']
    df = pd.DataFrame(data=data, columns=columns)
    
    for col in columns:
        if col != 'FLT' and col != 'FIELD':
            df[col] = pd.to_numeric(df[col])

    return df


# Read log file to get previous index
log_file = open('log.txt', 'r')
stamp_path_index = int(log_file.readline().split(':')[-1].strip())
log_file.close()

# Read stamp path file for list of all stamp paths
stamp_path_file = open('stamp_paths.txt', 'r')
stamp_paths = stamp_path_file.readlines()
stamp_path_file.close()

# Read master map of snids to objids
map_df = pd.read_csv('master_map.csv')

# Set path for dat file lookup
dat_file_path = '/data/des40.b/data/kherner/Nightly_Diffimg_postproc/Y6/Post-Processing/outputs_20180908_20190216/makedatafiles/LightCurvesReal/'

grabbed_enough_good_data = False
number_of_objects = 0
objects_considered = 0
meta_data = []
meta_data_cols = ['MJD', 'FLT', 'FLUXCAL', 'FLUXCALERR', 'PHOTFLAG', 'PHOTPROB',
                  'ZPFLUX', 'PSF', 'SKYSIG', 'SKYSIG_T', 'GAIN', 'XPIX', 'YPIX',
                  'EXPNUM', 'CCDNUM', 'OBJID', 'SNID']
while not grabbed_enough_good_data:

    # Update current stamp path
    stamp_path_index += 1

    # Grab the next stamp tarball and unpack it
    stamp_path = stamp_paths[stamp_path_index].strip()
    tarball = stamp_path.split('/')[-1]
    err_code = os.system('scp rmorgan@des40.fnal.gov:{} Stamps >> commands.log'.format(stamp_path))
    if err_code != 0:
        # if the internet times out, just send what we have so far
        print("Connection timed out. Sending what has already been organized")
        break

    os.chdir('Stamps')
    os.system('tar -xzf {}'.format(tarball))
    os.chdir('..')

    # Get the candidate objids
    objids = [x.split('srch')[-1].split('.')[0] for x in glob.glob('Stamps/srch*.gif')]
    objects_considered += len(objids)

    # Iterate through stamps and grab and check dat files
    objid_counter = 0
    for objid in objids:
        objid_counter += 1

        # Display progress
        msg = 'STATUS: '
        msg += 'Stamp Set ' + str(stamp_path_index) + ' - '
        msg += 'Good Objects ' + str(number_of_objects) + ' - '
        msg += 'Total Objects ' + str(objects_considered)
        sys.stdout.write('\r' + msg)
        sys.stdout.flush()

        # Check that all 3 stamps are present and accounted for
        stamps = glob.glob('Stamps/*{}.gif'.format(objid))
        if len(stamps) != 3:
            continue

        # Get the snid from the master lookup table
        try:
            snid = str(map_df['SNID'].values[map_df['SNOBJID'].values == int(objid)][0])
        except:
            continue
        
        # Download the dat file
        dat_file_name = dat_file_path + 'des_real_0' + snid + '.dat'
        err_code = os.system('scp rmorgan@des40.fnal.gov:{} DataFiles >> commands.log 2>&1'.format(dat_file_name))
        if err_code != 0:
            continue

        # Parse the dat file and check that the objid is present
        dat_file_lines = open_dat('DataFiles/des_real_0' + snid + '.dat')
        lc = get_terse_lc(dat_file_lines)
        lc = lc[np.array(lc['OBJID'].values, dtype=int) == int(objid)]
        if lc.shape[0] == 0:
            continue

        # Trim lc to only entries with ML SCORE > 0.9
        lc = lc[lc['PHOTPROB'].values > 0.8].copy().reset_index(drop=True)
        if lc.shape[0] == 0:
            continue
        
        # If we get here, everything is good, so extract data from dat file
        meta_data.append([lc['MJD'].values[0],
                          lc['FLT'].values[0],
                          lc['FLUXCAL'].values[0],
                          lc['FLUXCALERR'].values[0],
                          lc['PHOTFLAG'].values[0],
                          lc['PHOTPROB'].values[0],
                          lc['ZPFLUX'].values[0],
                          lc['PSF'].values[0],
                          lc['SKYSIG'].values[0],
                          lc['SKYSIG_T'].values[0],
                          lc['GAIN'].values[0],
                          lc['XPIX'].values[0],
                          lc['YPIX'].values[0],
                          lc['EXPNUM'].values[0],
                          lc['CCDNUM'].values[0],
                          int(objid),
                          int(snid)])

        # Update number of good objects
        number_of_objects += 1

        # Move the stamp set to MatchedStamps
        os.system('cp Stamps/*{}.gif MatchedStamps'.format(objid))

        # A fraction of the time, send the stamp set to my_labels
        random_integer = random.randint(1, 10)
        if random_integer == 6:
            os.system('cp Stamps/*{}.gif my_labels/stamps'.format(objid))

    # Delete unmatched stamps to avoid overlap
    err_code = os.system('rm Stamps/*')
    if err_code != 0:
        os.system('rm Stamps/*.gz')
        for ii in range(10):
            err_1 = os.system('rm Stamps/*{}.gif'.format(ii))
            err_2 = os.system('rm Stamps/*{}.fits'.format(ii))
            if err_1 != 0 or err_2 != 0:
                print("Exiting to prevent duplicates in Stamps/ directory")
                sys.exit()

    if number_of_objects > 500:
        grabbed_enough_good_data = True

# Update the log file to track the stamp path we left off at
log_file = open('log.txt', 'w+')
log_file.write('Previous stamp path index: ' + str(stamp_path_index))
log_file.close()

# Save metadata to a csv
meta_data_df = pd.DataFrame(data=meta_data, columns=meta_data_cols)
meta_data_outfile = 'MetaData/{}.csv'.format(timestamp)
meta_data_df.to_csv(meta_data_outfile, index=False)

# Tar up all the stamps that have been matched
os.mkdir('MatchedStamps/' + timestamp)
os.system('mv MatchedStamps/*.gif MatchedStamps/' + timestamp)
os.chdir('MatchedStamps')
os.system('tar -czf {0}.tar.gz {1}'.format(timestamp, timestamp))
os.chdir('..')

# Get a Kerberos ticket for HEP cluster
garb = input("\nDone! Press ENTER to continue.")
os.system('kinit ramorgan2@HEP.WISC.EDU')

# Send stamps and metadata to DES_DATA directory on HEP cluster
os.system('scp MatchedStamps/{}.tar.gz ramorgan2@login04.hep.wisc.edu:/afs/hep.wisc.edu/bechtol-group/ArtifactSpy/ImageBank/Tarballs >> commands.log'.format(timestamp))
os.system('scp MetaData/{}.csv ramorgan2@login04.hep.wisc.edu:/afs/hep.wisc.edu/bechtol-group/ArtifactSpy/Results/Metadata >> commands.log'.format(timestamp))

# Clean up files on local machine
os.system('rm DataFiles/*.dat')
os.system('rm MatchedStamps/*.tar.gz')
os.system('rm -rf MatchedStamps/' + timestamp)

# Trigger organize.py on HEP Cluster to sort new data
os.system("ssh ramorgan2@login04.hep.wisc.edu '/afs/hep.wisc.edu/bechtol-group/ArtifactSpy/organize_sort.py'")
