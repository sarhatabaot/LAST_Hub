# Scheduler operations

The scheduler is running continuously as a service on **last0**, and **the observer doesn't need to launch it** in a matlab session. You can check that everything is ok with ssh commands like

`last-asroot "service LAST_Scheduler status" -H last0`

If status is not "active", you may want to restart it with
`service LAST_Scheduler restart`

You can check the log showing how targets get requested and assigned, e.g. with

`last-asroot -H last0 "tail -f /var/log/syslog | grep target-scheduler"`

as well as with

`ssh ocs@10.23.1.25 "journalctl -u LAST_Scheduler.service"`

Note that you can also talk to the scheduler while it is running, sending commands or asking information, e.g.

`~/matlab/LAST/LAST_Messaging/doc/MessengerQuery.sh last0 12000 Scheduler.Ntarget`

`~/matlab/LAST/LAST_Messaging/doc/MessengerQuery.sh last0 12000 "Scheduler.List.Table(1,:)"`

and, notably, to purge old targets from the target list

`~/matlab/LAST/LAST_Messaging/doc/MessengerQuery.sh last0 12000 "Scheduler.cleanTargets;"`

This is within limits, experimental yet. Let Enrico know if you're interested in specific extensions.

## From the observer point of view

After focusing, run this command in the main MATLAB session in which you control the SuperUnit: 

`S.send("Unit.observeAskingTargets",n_mount)`

or, for focus by temperature mode:

```matlab
S.send("Unit.observeAskingTargets('FocusOnTemperatureGradient',true,'FocusOnTemperatureAfter',0.2);",n_mount)
```

This command can be sent to a single mount or all mounts, and it will instruct the mount to follow the targets assigned by the Scheduler.
Now relax, no more changing target lists. Monitor the observations to check if anything stops/disconnects and check the weather.
