# Flat fields and first focus loop (at sunset)

At sunset, when the observatory is open and only if the sky is clear, it’s time to take twilight flat frames. To do so, type

`S.send("Unit.operateUnit")`

This script will run a sanity check of the whole unit, then when possible will take flat fields and only when the sky is dark enough will take a focus loop for all telescopes. If you need to run it only for a specific mount, add the usual mount_num.

x§

To take only the flat field images, for a specific mount and specific cameras, type

`S.send("Unit.takeTwilightFlats([cameras_num])",mount_num)`

This will move the mount to a preferred position and then will take the images.
