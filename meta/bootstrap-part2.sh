#!/bin/bash
# vim:encoding=utf-8:ts=2:sw=2:expandtab

pushd /opt/acn-linux

echo 'Install [vim-enhanced, python33]'
yum install -y vim-enhanced python33 --enablerepo=ius-testing

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

popd