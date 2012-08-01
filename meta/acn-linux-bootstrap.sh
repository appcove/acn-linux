#!/bin/bash
# vim:encoding=utf-8:ts=2:sw=2:expandtab

echo 'Install EPEL'
rpm -Uvh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-7.noarch.rpm

echo 'Install IUS'
rpm -Uvh http://dl.iuscommunity.org/pub/ius/stable/Redhat/6/x86_64/ius-release-1.0-10.ius.el6.noarch.rpm

echo 'Install git and python32'
yum install git python32 --enablerepo=ius-testing

echo 'cd to /opt'
cd /opt

if [ -d acn-linux ]; then
  rm -rf acn-linux
fi

echo 'Clone acn-linux'
git clone git://github.com/appcove/acn-linux.git

F="/etc/profile.d/acn-linux-manual.sh"
echo "Install $F"
echo 'pathmunge /opt/acn-linux/bin' > $F

F="/usr/lib64/python2.6/site-packages/acn-linux-manual.pth"
echo "Install $F"
echo '/opt/acn-linux/python2.6' > $F

F="/usr/lib64/python3.2/site-packages/acn-linux-manual.pth"
echo "Install $F"
echo '/opt/acn-linux/python3.2' > $F


echo "Done!"


