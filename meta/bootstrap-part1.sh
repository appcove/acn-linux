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

echo 'cd to /opt'
pushd /opt

if [ -d acn-linux ]; then
  rm -rf acn-linux
fi

echo 'Install [git]'
yum install -y git --enablerepo=ius-testing

echo 'Clone acn-linux'
git clone git://github.com/appcove/acn-linux.git
popd

pushd /opt/acn-linux
echo "Getting remote branches"

for i in $(git branch -r | cut -f2 -d '>' | cut -f2 -d '/' | sed 's/[^a-zA-Z0-9]//g'); do git checkout $i -q; git fetch -q; done
echo "Enter branch or commit (enter defaults to master): "
x=1
for commit in $(git branch -r | cut -f2 -d '>' | cut -f2 -d '/' | sed 's/[^a-zA-Z0-9]//g')
do
  branches[$x]=${commit}
  echo $((x++)). $commit
done

while read -r userchoice; do
	if [[ $userchoice = "" ]]; then
      git checkout master
	else
	  git checkout ${userchoice}
	fi 

    if [ $? -eq 0 ]; then
		break
	else
		echo "Unable to checkout branch or commit ${userchoice}. Please try again"
	fi
done

popd

bashpath=$(which bash)
$bashpath /opt/acn-linux/meta/bootstrap-part2.sh