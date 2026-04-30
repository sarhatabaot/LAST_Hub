# Before observations

These are some basic preparation steps to have before any observations. Unless explicitly written, all these operations DO NOT need to be executed on Last0. Any last computer in the observatory network is good.

1. Hardware checks: check if all the machines see all the extension cards (2 per machine):

   ```bash
   last-asocs "lspci | grep Rene"
   ```
2. Run the MultiPanel to monitor the observatory status. Open this link in a web browser: <http://10.23.1.25>
3. ssh to any of the LAST machines (10.23.1.1-25) and open a matlab session in the shell

   ```bash
   matlab -nodesktop -nosplash
   ```
4. Initialize the superunit object with configurations

   ```matlab
   S=obs.superunit('1to10')
   ```

   ignore warnings if printed.
5. Spawn the Unit for each mount and create the communication infrastructure

   ```matlab
   S.spawn([1:6,10])
   ```
