# Roof Walls

Control the roof and walls using the Enclosure object through MATLAB running on LAST0.

* (for troubleshooting) check that the service last_enclosure_control is running on last0: ssh ocs@10.23.1.25 and
  `$ sudo service last_enclosure_control status`
  It should show Active: active (running). If not, report.

* commands are given from the shell from any last computer. The syntax is slightly different from before. The commands are still matlab commands, but the object is called Enclosure. Moreover, the command is written as an argument to the shell command last-enclosure-command.

 Examples:
```bash
$ last-enclosure-command Enclosure.openRoof
$ last-enclosure-command Enclosure.stopWalls
$ last-enclosure-command Enclosure  # returns the full status
$ last-enclosure-command Enclosure.HVAC # status of AC
$ last-enclosure-command Enclosure.AutoCloseAtSunrise=false  # disable auto closing
$ last-enclosure-command "Enclosure.closeWalls('NS')" # mind the quotes!
```

**During observations:**
* the roof is open
* the eastern wall is down (open)
* the northern and southern walls should be raised (closed) to protect the telescopes from the wind. Only for low targets the walls can be opened.
* The AC is closed.

**After observations**
* the roof is closed.
* the eastern, northern and southern walls are up (closed)
* The AC is open.
