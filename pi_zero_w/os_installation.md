# SD Card installation

* Install the rpi-imager package 
* Write Raspberry Pi OS Lite (32-bit) to the SD card
    * Edit the settings
        * general
            * set hostname
            * username/password
            * wireless lan config
            * locale
        * services
            * enable ssh and use password authentication
* Modify the config.txt file on the boot partition
  * add `enable_uart=1` to the end of the file

# First boot
On the first boot the console should be redirected to the serial port.

Lots of messages for the first 20 seconds or so and then a long pause this is where
it is running the initial setup code...after three minutes it will restart.

