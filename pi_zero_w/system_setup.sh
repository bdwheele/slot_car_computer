#!/bin/bash

systemctl disable bluetooth.service
systemctl stop bluetooth.service

apt purge modemmanager

apt update
apt install -y python3-picamera2 python3-opencv
