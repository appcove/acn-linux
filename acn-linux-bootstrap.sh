#!/bin/bash

echo 'Install EPEL'
rpm -Uvh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-7.noarch.rpm

echo 'Install git'
yum install git

echo 'cd to /opt'
cd /opt

echo 'Clone acn-linux'
git clone git://github.com/appcove/acn-linux.git

PF="/etc/profile.d/acn-linux-manual.sh"
echo "Install $F"

> $F
echo 'pathmunge /opt/acn-linux/bin' >> $F


F="/usr/lib64/python2.6/site-packages/acn-linux-manual.pth"
echo "Install $F"

> $f
echo '/opt/acn-linux/python2.6/' >> $F

echo "Done!"


