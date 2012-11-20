acn-setup-mc

acn-setup-backup

------------------------------------------------------------------------------

Maybe a reminder about /etc/hosts needing checked for XXXX.YYY.COM and XXXX ?

-------------------------------------------------------------------------------
Rather than creating a default server in nginx.conf, ask if the user wishes to
place a server in conf.server.d/default.conf

------------------------------------------------------------------------------
Consider vim 2-space modeline at top of each file

-------------------------------------------------------------------------------
acn-setup-etcgit
1. ask if we should ignore .properties  (especially if using comvault)

-------------------------------------------------------------------------------

Consider multiple IPs on nginx conf, or removing the default server...

Having issues with a redirect site causing other non-existant sites on that
IP redirecting to an SSL site... Do not like that.


-------------------------------------------------------------------------------

Hello Jason,

I do not believe there is a option similar to 'enablerepo' in mock,
the way we handle building against testing is by having a separate configuration with enable=1 on
the testing repo.

If your intentions are building against IUS and IUS Testing I may suggest having two files,
one for ius-6-x86_64 (with testing disabled) and ius-6-x86_64_testing which has IUS and IUS Testing
enabled.

I believe BJ suggested Testing disabled because publicly not many users of IUS pull from Testing.

---
Jeffrey Ness
Software Developer II
OS Deployment Services, RPMDEV
Rackspace Hosting & IUS Community


-------------------------------------------------------------------------------

Changing Hostname... Research this

/proc/sys/kernel/hostname
/etc/hosts
/etc/sysconfig/network


------------------------------------------------------------------------------

Fresh install of oracle linux 6:

CALLING /opt/acn-linux/bin/acn-setup-ntpd

Setup ntpd to start automatically (yes)?
error reading information on service ntpd: No such file or directory


*** Fatal Error ***
Command '('chkconfig', 'ntpd', 'on')' returned non-zero exit status 1

------------------------------------------------------------------------------





