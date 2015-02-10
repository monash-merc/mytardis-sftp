mytardisfs
==========
The scripts in this repository form a prototype for making MyTardis data available in a FUSE virtual filesystem, which can be exported via SFTP (and related methods such as RSYNC over SSH).  After installing with "sudo python setup.py install", these scripts are accessible currently from within /usr/local/bin/ on my MyTardis server.  The main script is mytardisfs, which uses Python-Fuse to set up a virtual filesystem.  The mytardisftpd script is an easy way to call mytardisfs - it automatically chooses a mountpoint, ~/MyTardis, calls mytardisfs, and waits for the FUSE filesystem to be ready, returning 0 on success, and 1 if it's not ready after 10 seconds.  

Launching mytardisfs/mytardisftpd automatically for SFTP/SSHFS/RSYNC users
--------------------------------------------------------------------------
At present, the scripts are designed to be run by an ordinary user (whose POSIX username from LDAP matches their MyTardis username).  For interactive SSH login, mytardisftpd can be run automatically by placing it in /etc/profile.  For SFTP login, /etc/ssh/sshd\_config can be modified to point to a custom sftp-subsystem script, e.g. /usr/local/lib/openssh/sftp-server, instead of the default /usr/lib/openssh/sftp-server executable, and this custom script can start up mytardisftpd before running /usr/local/lib/sftp-server.  For RSYNC over SSH, you can use --rsync-path="/usr/local/bin/mytardisftpd && /usr/bin/rsync" to ensure that mytardisfs is available for the rsync.  For logging in with SSH keys, you can put executable commands next to your public keys in ~/.ssh/authorized\_keys.  SCP does not use the sftp-subsystem, but it does use ~/.bashrc, which may source /etc/bash.bashrc, so you can try to use /etc/bash.bashrc to start mytardisftpd, or alternatively, you can just log in with SSH first, and start mytardisftpd in the background using nohup to ensure that the process will persist after you exit the login shell.

LDAP
----
mytardisfs assumes that POSIX usernames can be mapped to MyTardis usernames, given a MyTardis authentication provider (e.g. test\_ldap), specified in /etc/mytardisfs.cnf.  This POSIX-to-MyTardis user mapping can be tested with MyTardis's 'localdb' authentication provider, but in practice, LDAP is the preferred way to grant both SFTP access (using a POSIX identity) and MyTardis access to users.  PAM and NSS can be configured on the MyTardis server to allow SSH/SFTP logins, using LDAP credentials.  This code has been run on Ubuntu 12.04.2 (Precise).  PAM and NSS were configured for LDAP, using these instructions: http://askubuntu.com/questions/127389/how-to-configure-ubuntu-as-an-ldap-client .  This means that the same credentials can be used to log into the MyTardis web interface and into the SFTP server.  

How the Python-Fuse process accesses MyTardis
---------------------------------------------
There are two different ways in which mytardisfs accesses MyTardis:

1. Using MyTardis's TastyPie RESTful API
2. Using Django (with some "sudo -u mytardis" trickery)

The API was the preferred method in early discussions with stakeholders, however it is not clear that we can get reasonable performance out of the API for serving up files via SFTP from a virtual FUSE filesystem.  The problem is that SFTP clients expect large files to begin downloading immediately (in small chunks), so they can update their progress dialogs.  The API doesn't have an efficient way to serve up a series of small chunks, and if the Python-Fuse process waits for the entire datafile to be served up by the API before making it available to the SFTP server, then the SFTP client can get confused and think that the connection to the SFTP server has stopped responding. 

The other method is to use Django to access the MyTardis data.  For example, the "\_datafiledescriptord" console descript, generated in setup.py from the "datafiledescriptord.py" module is designed to be run with "sudo -u mytardis", so that it can access the MyTardis file store directly, open a data file, and hand the file descriptor over to the unprivileged mytardisfs process.  The "datafiledescriptord.py" script checks the SUDO\_USER environment variable to determine the POSIX username calling the script, which is assumed to be the same as the MyTardis username.  To be more accurate, a MyTardis user can link multiple authentication methods e.g. username "jsmith" (using LDAP) and username "johns" (using localdb).  So if the "\_datafiledescriptord" script receives SUDO\_USER=jsmith, it looks up username="jsmith" in MyTardis's UserAuthentication model with auth\_method="cvl\_ldap".  Of course the auth\_method should be easily configurable, (e.g. as a command-line option to mytardisfs), but it is hard-coded for now.  Also the username mapping should be configurable, e.g. the POSIX username could be "jsmith", but the MyTardis username could be "jsmith@example.org".

To allow regular users to run scripts like "\_datafiledescriptord", we need to add a rule into /etc/sudoers.  *BE CAREFUL EDITING THIS FILE - USE visudo OR sudoedit TO ENSURE THAT YOU DON'T ACCIDENTALLY CREATE A SYNTAX ERROR WHICH COMPLETELY DISABLES YOUR SUDO ACCESS.*  Rules in /etc/sudoers are read in order from top to bottom, so if you add a 
rule down the bottom, then you can be sure that it won't be overwritten by any subsequent rules.
```
ALL     ALL=(mytardis:mytardis) NOPASSWD: /usr/local/bin/_myapikey, /usr/local/bin/_datafiledescriptord, /usr/local/bin/_datasetdatafiles, /usr/local/bin/_countexpdatasets

```

If you're wondering why we have an arbitrary looking "\_datasetdatafiles" script (which as the name suggests, queries MyTardis for a list of datafiles belonging to a given dataset), it is because most queries like this are currently done with the TastyPie RESTful API.  But just recently, I have been testing whether it is actually faster to do these queries using the Django models instead.

Security/Privacy Concerns
-------------------------

You are probably accustomed to avoiding letting users log onto the server where you run your web application, and generally this is wise, because you don't want users wasting resources (disk, memory, CPU) which could compete with your web application, and you don't want malicious users to take advantage of a mistake the web administrator has made where permissions may be too open on sensitive data files or configuration files.  At present, this MyTardis SFTP solution must run on the MyTardis server - so that SFTP clients which request the first chunk of a MyTardis data file can get an immediate response.  You should check that your MyTardis file store is only readable by the "mytardis" user, not by any of your LDAP users.  Restricting access to the MyTardis application's directory (usually /opt/mytardis/current/) to the "mytardis" user may not work because the static content in /opt/mytardis/current/static/ needs to be accessible by the web server user (e.g. "nginx"), not just "mytardis".  Chrooting is one approach to keeping users away from parts of the filesystem they shouldn't be able to access, and it could work well with MyTardis SFTP if it were purely using MyTardis's RESTful API, but given that it currently uses Django as well, you would need to run mytardisftpd outside of the chroot before the user enters the chroot, but ensure that doing so doesn't allow the user to bypass the chroot, e.g. by pressing Contrl-C while the pre-chroot mytardisftpd script is running.

Changes to TastyPie API
-----------------------

MyTardisFS needs to be able to filter datasets based on experiment ID.  To achieve this, the following changes were made to api.py:
```
diff --git a/tardis/tardis_portal/api.py b/tardis/tardis_portal/api.py
index 58dcdd0..53eee08 100644
--- a/tardis/tardis_portal/api.py
+++ b/tardis/tardis_portal/api.py
@@ -517,6 +517,7 @@ class ExperimentResource(MyTardisModelResource):
     class Meta(MyTardisModelResource.Meta):
         queryset = Experiment.objects.all()
         filtering = {
+            'id': ('exact', ),
             'title': ('exact',),
         }
 
@@ -607,6 +608,7 @@ class DatasetResource(MyTardisModelResource):
         queryset = Dataset.objects.all()
         filtering = {
             'id': ('exact', ),
+            'experiments': ALL_WITH_RELATIONS,
             'description': ('exact', ),
             'directory': ('exact', ),
         }
```
