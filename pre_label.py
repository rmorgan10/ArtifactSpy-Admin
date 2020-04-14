# Label a subset of matched stamps to evaluate user accuracy

import glob
import os
import pandas as pd
import sys

sys.path.append('ArtifactSpy/Code/')
import viewer

# Print warning
print("Don't forget, you were too lazy to make the back button work for this script, so do not use it\n")

# Get objids to be labeled
objids = [x.split('srch')[-1].split('.')[0] for x in glob.glob('my_labels/stamps/srch*.gif')]
path = 'my_labels/stamps/'

# For each objid, label it and store the outputs
out_data = []
out_data_cols = ['OBJID', 'LABEL', 'RM_COMMENT']
finished_objids = []

for counter, objid in enumerate(objids):
    print(counter + 1, '/', len(objids), '  ')
    
    gui = viewer.Interface(objid, path=path)

    # A hack to escape if need be, use it wisely
    if gui.user_action == "Other":
        if gui.user_comment.strip().lower() == 'exit':
            break
    
    if gui.user_action == 'Back':
        print("What are you doing? I literally told you not to do that.")
        print("Lucky for you, I expected you to be a fool.")
        print("Do it right this time, please.")
        choice = gui.user_action
        while choice == "Back":
            gui = viewer.Interface(objid, path=path)
            choice = gui.user_action
        print("There, thanks for getting it right, doofus.")

    if gui.user_comment is not None:
        out_data.append([objid, gui.user_action, gui.user_comment])
    else:
        out_data.append([objid, gui.user_action, ""])

    finished_objids.append(objid)

out_df = pd.DataFrame(data=out_data, columns=out_data_cols)

# Load in and concatenate existing my_labels
if os.path.exists('my_labels/my_labels.csv'):
    existing_df = pd.read_csv('my_labels/my_labels.csv')
    out_df = pd.concat([existing_df, out_df])

# Save labels
out_df.to_csv('my_labels/my_labels.csv', index=False)

# Send to HEP cluster
os.system('scp my_labels/my_labels.csv ramorgan2@login04.hep.wisc.edu:/afs/hep.wisc.edu/bechtol-group/ArtifactSpy/Results/ramorgan2')

# Clean up finished images
cleanup = input("All done. Do you want to remove the finished images? (yes / no)")
while cleanup not in ['yes', 'no']:
    print("Please answer 'yes' or 'no'.")
    cleanup = input("All done. Do you want to remove the finished images? (yes / no)")

if cleanup == 'yes':
    for objid in finished_objids:
        os.system('rm my_labels/stamps/*{}.gif'.format(objid))
