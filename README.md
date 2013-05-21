
acn-linux
=========

AppCove Network extensions for RedHat Enterprise Linux and similar.

* Designed to work with RHEL 6, Centos 6, Oracle Linux 6
* Useful tools and utilites relating to python, git, administration
* Quick install to /opt/acn-linux using bootstrap script
* RPMS may come eventually
* Apache License

## Getting Started

As root, copy and paste this line onto your terminal

```bash
curl -L 'https://raw.github.com/appcove/acn-linux/master/meta/bs1.sh' > acnsh && bash acnsh && . /etc/profile
```

This does several things:

1. Install EPEL
2. Install git
3. Clone acn-linux into /opt/acn-linux
4. Append to the python sys.path (/opt/acn-linux/python2.6)
5. Append to the system $PATH (/opt/acn-linux/bin)


To start the setup process
==========================

As root

```bash
acn-setup
```

This will guide you through each setup step.  We recommend you run 
them in order, as some depend on others.  

Command Reference
-------------------------------------

### acn-setup
Calling program used to call other programs.

### acn-setup-timezone
Set the system timezone.  US/Eastern is the default.  This command shows you the time before and after it is run, so any issues may be spotted.

Usage Example: 

    # acn-setup-timezone

    The Time is: Mon Nov 19 22:30:25 EST 2012

    Set the timezone (yes)?
    Enter the timezone (US/Eastern): US/Pacific

    NOW, the Time is: Mon Nov 19 19:30:32 PST 2012


How it works:

1. Ask user for valid timezone.  Verify against `/usr/share/zoneinfo/*/*`
2. Update the ZONE line in /etc/sysconfig/clock
3. run tzdata-update, which updates /etc/localtime

### acn-update-self 

Update to the latest version of ACN.  It is assuming you are sitting on the `master` branch, so if you are not, it will not work as expected.

Usage Example:

    # acn-update-self

    Do you want to update "/opt/acn-linux" to the latest? (yes)?
    remote: Counting objects: 11, done.
    remote: Compressing objects: 100% (1/1), done.
    remote: Total 6 (delta 5), reused 6 (delta 5)
    Unpacking objects: 100% (6/6), done.
    From git://github.com/appcove/acn-linux
       5b3d1eb..c91c781  master     -> origin/master
    Updating 5b3d1eb..c91c781
    Fast-forward
     README.md              |   36 ++++++++++++++++++++++++++++++++++++
     TODO.md                |   15 ---------------
     bin/acn-setup-timezone |   10 ++++++++--
     3 files changed, 44 insertions(+), 17 deletions(-)

How it works:

1. Change to the /opt/acn-linux directory
2. Run `git pull`




-----------------------------


vim:encoding=utf-8:ts=2:sw=2:expandtab

