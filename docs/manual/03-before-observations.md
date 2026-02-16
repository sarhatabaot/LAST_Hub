# Before Observations

0. Hardware checks:
   Check if all the machines see all the extension cards (2 per machine):
   `last-asocs "lspci | grep Rene"` 

These are some basic preparation steps to have before any observations. Unless explicitly written, all these operations DO NOT need to be executed on Last0. Any last computer in the observatory network is good.

1. Run the MultiPanel to monitor the observatory status.
   Open this link in a web browser: http://10.23.1.25
2. ssh to any of the LAST machines (10.23.1.1-25) and open a matlab session in the shell
   `matlab -nodesktop -nosplash`
3. Initialize the superunit object with configurations
   `S=obs.superunit('1to10')`
   ignore warnings if printed.
4. Spawn the Unit for each mount and create the communication infrastructure
   `S.spawn([1:6,10])`
