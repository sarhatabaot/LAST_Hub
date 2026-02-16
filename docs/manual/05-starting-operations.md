# Starting Operations

Wait until the Sun is below the horizon!
Start by spawning the mounts:
`S.spawn(mount_num)`
Now it’s time to connect the Units. Every command will be given by the superunit using the following format:

`S.send("YourCommand",mount_num)`

Example of the “connect” command to several units:

`S.send("Unit.connect",[1:6,8,10])` %connects units from 1 to 6, 8 and 10.
