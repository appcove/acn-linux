#!/bin/bash
# vim:fileencoding=utf-8:ts=2:sw=2:expandtab

pushd /opt/acn-linux

echo 'Install [vim-enhanced, python36u]'
yum install -y vim-enhanced python36u python36u-devel.x86_64 python36u-libs python36u-pip python36u-redis python36u-setuptools python36u-tkinter.x86_64	python36u-tools

F="/etc/profile.d/acn-linux.sh"
echo "Install $F"
echo 'pathmunge /opt/acn-linux/bin' > $F

F="/etc/profile.d/acn-linux-vim.sh"
echo "Install $F"
echo 'alias vi=vim' > $F
echo 'export EDITOR=/usr/bin/vim'

F="/usr/lib64/python3.6/site-packages/acn-linux.pth"
echo "Install $F"
echo '/opt/acn-linux/python3.6' > $F


echo "--- Done! ---"
echo "The next step would be to run: "
echo "  acn-setup"
echo 

popd
