# LAST Hub

Central location for all apps, services, documentation. 

To add the service:
```bash
sudo cp last-hub.service /etc/systemd/system/last-hub.service
sudo systemctl daemon-reload
sudo systemctl enable last-hub-service
sudo systemctl start last-hub-service
sudo systemctl status last-hub-service
```
