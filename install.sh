#!/bin/sh

mkdir /usr/local/bin/backups
cp ./* /usr/local/bin/backups/

cp ./backups.sh /etc/init.d/