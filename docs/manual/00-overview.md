# Overview

## What is the SuperUnit?
The superunit acts mostly as a broker for all the classes and functions that we used in the previous single-mount control of LAST. Basic methods to send commands are

```matlab
S.send('TheCommand',mount_num)
```


and to query outputs from methods

```matlab
S.query('TheCommand',mount_num)
```
where mount_num is the number of the mount or, if not specified, the command will be sent to all mounts.

An overview of LAST commands can be found in the LAST operation manual.

