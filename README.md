# Gister Bot
## Description
C&C CLI controller and bot that use gist.github.com for communication.
The bot uses comments under a given Gist to communicate with the controller.  
To evade detection, all intervals for pinging and checking new messages are randomized and some steganography is used (links in markdown are not shown if the alternate text field is empty).  
If a message was "consumed" (read and responded to), it is immediately removed from the Gist comment thread.

## Disclaimer
This project was made for educational purposes only as a part of the B4M36BSY course on the Faculty of Electrical Engineering, Czech Technical University in Prague.