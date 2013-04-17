#!/bin/bash
# vim:encoding=utf-8:ts=2:sw=2:expandtab

echo 'Install EPEL'
rpm -Uvh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm

OS=$(lsb_release -si | tr '[:upper:]' '[:lower:]' | tr -d ' ')
if [[ "$OS" == *centos* ]]; then
    rpm -Uvh http://dl.iuscommunity.org/pub/ius/stable/CentOS/6/x86_64/ius-release-1.0-11.ius.centos6.noarch.rpm	
else
	rpm -Uvh http://dl.iuscommunity.org/pub/ius/stable/Redhat/6/x86_64/ius-release-1.0-11.ius.el6.noarch.rpm
fi

echo 'Install [git, vim-enhanced, python33]'
yum install -y git vim-enhanced python33 --enablerepo=ius-testing

echo 'cd to /opt'
cd /opt

if [ -d acn-linux ]; then
  rm -rf acn-linux
fi

echo 'Clone acn-linux'
git clone git://github.com/appcove/acn-linux.git

F="/etc/profile.d/acn-linux.sh"
echo "Install $F"
echo 'pathmunge /opt/acn-linux/bin' > $F

F="/etc/profile.d/acn-linux-vim.sh"
echo "Install $F"
echo 'alias vi=vim' > $F
echo 'export EDITOR=/usr/bin/vim'

F="/usr/lib64/python2.6/site-packages/acn-linux.pth"
echo "Install $F"
echo '/opt/acn-linux/python2.6' > $F

F="/usr/lib64/python3.3/site-packages/acn-linux.pth"
echo "Install $F"
echo '/opt/acn-linux/python3.3' > $F


echo "--- Done! ---"
echo "The next step would be to run: "
echo "  acn-setup"
echo 



