#!/usr/bin/python

# Displays the number of datasets in a given experiment, assuming that
# the user has access to that experiment, otherwise, displays an error.

# A client process, running as a regular LDAP username (matching a MyTardis
# username) runs this script, which runs as user "mytardis", via
# "sudo -u mytardis", thanks to a rule within /etc/sudoers.

# This script can determine the username which the client script is
# running as, thanks to the SUDO_USER environment variable, so it will
# only provide access to experiment IDs available to that MyTardis
# username.  Currently the username is matched using the "cvl_ldap"
# authentication scheme in our MyTardis deployment
# (defined in [mytardis_install_dir]/tardis/settings.py)

import os
import sys
import getpass
import traceback


def run():
    if getpass.getuser() != "mytardis" or "SUDO_USER" not in os.environ:
        print "Usage: sudo -u mytardis _countexpdatasets" + \
            "mytardis_install_dir auth_provider"
        sys.exit(1)

    if len(sys.argv) < 3:
        print "Usage: sudo -u mytardis _countexpdatasets" + \
            "mytardis_install_dir auth_provider"
        sys.exit(1)

    _mytardis_install_dir = sys.argv[1].strip('"')
    _auth_provider = sys.argv[2]

    sys.path.append(_mytardis_install_dir)
    for egg in os.listdir(os.path.join(_mytardis_install_dir, "eggs")):
        sys.path.append(os.path.join(_mytardis_install_dir, "eggs", egg))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'tardis.settings')

    from tardis.tardis_portal.models import Experiment
    from tardis.tardis_portal.models import UserAuthentication
    from django.core.exceptions import ObjectDoesNotExist

    found_user = False
    mytardis_user = None
    exp_public = False
    exp_owned_or_shared = False
    staff_or_superuser = False
    try:
        userAuth = UserAuthentication.objects \
            .get(username=os.environ['SUDO_USER'],
                 authenticationMethod=_auth_provider)
        mytardis_user = userAuth.userProfile.user
        # logger.debug("Primary MyTardis username: " + mytardis_user.username)
        # print "Primary MyTardis username: " + mytardis_user.username
        found_user = True
        staff_or_superuser = mytardis_user.is_staff or \
            mytardis_user.is_superuser
        exp_dict = dict()

        exps_owned_and_shared = Experiment.safe \
            .owned_and_shared(mytardis_user)
        exps = Experiment.objects.all()
        for exp in exps:
            if staff_or_superuser or exp in exps_owned_and_shared or Experiment \
                    .public_access_implies_distribution(exp.public_access):
                dataset_count = exp.datasets.count()
                exp_dict[exp.id] = dataset_count
        print str(exp_dict)
    except ObjectDoesNotExist:
        print traceback.format_exc()
        # print "User " + os.environ['SUDO_USER'] + " \
        #    was not found in MyTardis."
    except:
        print traceback.format_exc()
