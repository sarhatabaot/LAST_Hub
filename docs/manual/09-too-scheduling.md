# How to schedule a ToO

To dynamically insert new high-priority targets into the observing schedule, you can inject a ToO CSV file. This file must follow the same structure as the standard observation schedule file.
* The scheduler **periodically monitors** for the file /home/ocs/Scheduler/ToO.csv.

If the ToO.csv file is found:
1. It will ingest all targets listed in the file and add them to the schedule.
2. The file will then be automatically deleted after successful import.

This allows real-time or near-real-time insertion of high-priority observations without restarting the system.
1. Download the ToO template here and insert your ToO. Do not delete the row with the column names. 
2. Save your csv as `/home/ocs/Scheduler/ToO.csv`

Note: The ToO scheduler will only recognize the file once, so make sure it’s correctly formatted and finalized before saving it to the target location. Please document every injection in the shifter log.