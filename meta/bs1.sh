#!/bin/bash
# vim:fileencoding=utf-8:ts=2:sw=2:expandtab

echo 'Install EPEL'
rpm -Uvh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

OS=$(lsb_release -si | tr '[:upper:]' '[:lower:]' | tr -d ' ')
if [[ "$OS" == *centos* ]]; then
  rpm -Uvh https://centos7.iuscommunity.org/ius-release.rpm 
else
  rpm -Uvh https://rhel7.iuscommunity.org/ius-release.rpm
fi

echo 'cd to /opt'
pushd /opt

if [ -d acn-linux ]; then
  rm -rf acn-linux
fi

echo 'Install [git]'
yum install -y git2u

echo 'Clone acn-linux'
git clone git://github.com/appcove/acn-linux.git
popd

pushd /opt/acn-linux
echo "Getting remote branches..."


while true; do
  git branch -r

  echo
  echo "Please enter a git branch, tag, or commit to use, or simply press enter to use origin/HEAD: "

  read -r userchoice
   
  # If the user enters nothing, then we are already on HEAD, and that is fine.
  # Otherwise, try to check it out and repeat on failure.
  if [[ $userchoice = "" ]]; then
    break
  else
    basechoice=$(basename $userchoice)
    git checkout -b ${basechoice} --no-track ${userchoice}
  
    # If the git checkout was successful, then break.  Otherwise, repeat the question.
    if [ $? -eq 0 ]; then
      break
    else
      echo
      echo
      echo "Unable to checkout branch or commit ${userchoice}. Please try again."
      echo
    fi
  fi 

done

popd

bashpath=$(which bash)
$bashpath /opt/acn-linux/meta/bs2.sh

