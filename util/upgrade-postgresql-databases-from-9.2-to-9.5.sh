#!/bin/bash

if [ $USER != 'postgres' ]; then
  echo 'must run as postgres user'
  exit 1
fi

/usr/pgsql-9.5/bin/pg_upgrade -b /usr/pgsql-9.2/bin/ -B /usr/pgsql-9.5/bin/ -d /var/lib/pgsql/9.2/data/ -D /var/lib/pgsql/9.5/data/

