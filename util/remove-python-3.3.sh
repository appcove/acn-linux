#!/bin/bash

if [ $USER != 'root' ]; then
  echo 'must run as root user'
  exit 1
fi

yum remove python33-libs
rm /etc/httpd/conf.d/python33-mod_wsgi.conf.rpm*


