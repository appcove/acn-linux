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
pushd /opt

if [ -d acn-linux ]; then
  rm -rf acn-linux
fi

echo 'Clone acn-linux'
git clone git://github.com/appcove/acn-linux.git
popd

pushd /opt/acn-linux
echo "Getting remote branches"
for i in $(git branch | sed 's/^.//'); do git checkout $i -q; git fetch -q; done

echo "Which branch would you like to use (enter defaults to master): "
x=1
for commit in $(git branch | sed 's/^.//')
do
  branches[$x]=${commit}
  echo $((x++)). $commit
done
read userchoice
if [[ $userchoice -ge 1 && $userchoice -lt ${#branches[@]} ]]; then
  git checkout ${branches[$userchoice]}
else
  git checkout master
fi

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

