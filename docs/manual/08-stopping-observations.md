# Stopping Observations

To stop observations while they are instructed by the scheduler, simply go to the MATLAB session that control the SuperUnit and type

```matlab
S.abortActivity(n_mount)
```

And wait until each mount you included in the command shows the status “releasing abortActivity”.
Now you can re-focus, shutdown the mount or do any operation you need to. 
