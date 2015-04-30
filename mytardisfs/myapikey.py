#!/usr/bin/python

# Filename: myapikey.py
# Author: James Wettenhall <james.wettenhall@monash.edu>
# Description: Used by mytardisfs to obtain a user's API key.

import sys
import os
import getpass


def run():
    # This script should be run as user 'mytardis' via sudo.
    # All users have permission to run it as sudo without a password,
    # thanks to this line in /etc/sudoers:
    # ALL     ALL=(ALL) NOPASSWD: /usr/local/bin/_myapikey,
    #    /usr/local/bin/_datafiledescriptord, /usr/local/bin/_datasetdatafiles

    if getpass.getuser() != "mytardis" or "SUDO_USER" not in os.environ:
        print "Usage: sudo -u mytardis _myapikey " + \
            "mytardis_install_dir auth_provider"
        os._exit(1)

    if len(sys.argv) < 3:
        print "Usage: sudo -u mytardis _myapikey " + \
            "mytardis_install_dir auth_provider"
        sys.exit(1)

    _mytardis_install_dir = sys.argv[1].strip('"')
    _auth_provider = sys.argv[2]

    sys.path.append(_mytardis_install_dir)
    for egg in os.listdir(os.path.join(_mytardis_install_dir, "eggs")):
        sys.path.append(os.path.join(_mytardis_install_dir, "eggs", egg))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'tardis.settings')

    from tardis.tardis_portal.models import UserAuthentication
    from tastypie.models import ApiKey

    userAuth = UserAuthentication.objects \
        .get(username=os.environ['SUDO_USER'],
             authenticationMethod=_auth_provider)
    myTardisUser = userAuth.userProfile.user

    key = ApiKey.objects.get(user__username=myTardisUser.username)
    print "ApiKey " + myTardisUser.username + ":" + str(key.key)
