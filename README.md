acn-linux
=========

AppCove Network extensions for RedHat Enterprise Linux and similar.

* Designed to work with RHEL 6, Centos 6, Oracle Linux 6
* Useful tools and utilites relating to python, git, administration
* Quick install to /opt/acn-linux using bootstrap script
* RPMS may come eventually
* Apache License

## Getting Started

As root, copy and paste these five lines onto your terminal

```bash
cd /root 
wget https://github.com/appcove/acn-linux/raw/master/meta/acn-linux-bootstrap.sh 
/bin/bash acn-linux-bootstrap.sh
source /etc/profile
rm -f acn-linux-bootstrap.sh
```

This does several things:

1. Install EPEL
2. Install git
3. Clone acn-linux into /opt/acn-linux
4. Append to the python sys.path (/opt/acn-linux/python2.6)
5. Append to the system $PATH (/opt/acn-linux/bin)


acn-setup-iptables
==================

This script will assist you in installing and enabling iptables.  

Call it by typing (as root) `acn-setup-iptables`.

IP addresses should be entered in `1.2.3.4` or `1.2.3.4/32` format.


