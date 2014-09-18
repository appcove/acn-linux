# vim:encoding=utf-8:ts=2:sw=2:expandtab
import csv
import boto3
import botocore


def GetSession(credsfilename='', access_key='', secret_key=''):
    # Get keys
    if len(access_key) == 0:
        creds = []
        fields = None
        with open(credsfilename) as csvfile:
            csvreader = csv.reader(csvfile, dialect="excel")
            for i, row in enumerate(csvreader):
                if i == 0:
                    fields = row
                else:
                    creds.append(dict(zip(fields, row)))
            # We must have atleast one creds row
            assert len(creds) > 0
            # Build a session from which we extract connections
            credtouse = creds[0]
            access_key = credtouse[fields[1]]
            secret_key = credtouse[fields[2]]
    # Now we can build the session
    coresession = botocore.session.Session()
    coresession.set_credentials(access_key=access_key, secret_key=secret_key)
    session = boto3.Session(session=coresession)
    # Return the session
    return session


