#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
#
# Copyright: 2016 IBM
# Author: Venkat Rao B <vrbagal1@linux.vnet.ibm.com>
# Author: Narasimhan V <sim@linux.vnet.ibm.com>


"""
RAID devices are virtual devices created from two or more real block devices.
This allows multiple devices (typically disk drives or partitions thereof) to
be combined into a single device to hold (for example) a single filesystem.
Some RAID levels include redundancy and so can survive some degree of device
failure.
"""

import time
from avocado import Test
from avocado.utils.software_manager import SoftwareManager
from avocado.utils import process
from avocado import main


class SoftwareRaid(Test):

    """
    This scripts create, assembles and stops md device, using mdadm tool
    """

    def setUp(self):
        """
        Checking if the required packages are installed,
        if not found packages will be installed
        """

        smm = SoftwareManager()
        if not smm.check_installed("mdadm"):
            print "Mdadm must be installed before continuing the test"
            if SoftwareManager().install("mdadm") is False:
                self.cancel("Unable to install mdadm")
        cmd = "mdadm -V"
        self.check_pass(cmd, "Unable to get mdadm version")
        self.disk = self.params.get('disks', default='').strip(" ")
        self.raid = self.params.get('raidname', default='/dev/md/mdsraid')
        self.raidlevel = str(self.params.get('raid', default='0'))
        self.metadata = str(self.params.get('metadata', default='1.2'))
        self.setup = self.params.get('setup', default=True)
        self.run_test = self.params.get('run_test', default=False)
        self.cleanup = self.params.get('cleanup', default=True)
        self.sparedisk = ""
        if self.raidlevel == 'linear' or self.raidlevel == '0':
            self.disk_count = len(self.disk.split(" "))
        else:
            self.disk = self.disk.split(" ")
            self.sparedisk = self.disk.pop()
            self.remadd = ''.join(self.disk[-1:])
            self.disk_count = len(self.disk)
            self.disk = ' '.join(self.disk)
        self.force = self.params.get('force', default=False)

    def test_run(self):
        """
        Decides which functions to be run for a perticular raid level
        """
        if self.setup:
            self.create_raid()
        if self.run_test:
            if self.raidlevel != 'linear' and self.raidlevel != '0':
                self.extensivetest()

    def create_raid(self):
        """
        Only basic operations are run viz create and delete
        """
        cmd = "echo 'yes' | mdadm --create --verbose --assume-clean \
            %s --level=%s --raid-devices=%d %s --metadata %s" \
            % (self.raid, self.raidlevel, self.disk_count, self.disk,
               self.metadata)
        if self.sparedisk:
            cmd += " --spare-devices=1 %s " % self.sparedisk
        if self.force:
            cmd += " --force"
        self.check_pass(cmd, "Failed to create a MD device")
        cmd = "mdadm --detail %s" % self.raid
        self.check_pass(cmd, "Failed to display MD device details")

    def extensivetest(self):
        """
        Extensive software raid options are run viz create, delete, assemble,
        create spares, remove and add drives
        """
        cmd = "mdadm --fail %s %s" % (self.raid, self.remadd)
        self.check_pass(cmd, "Unable to fail a drive from MD device")
        cmd = "mdadm --detail %s" % self.raid
        self.check_pass(cmd, "Failed to display MD device details")
        cmd = "mdadm --manage %s --remove %s" % (self.raid, self.remadd)
        self.check_pass(cmd, "Failed to remove a drive from MD device")
        cmd = "mdadm --detail %s" % self.raid
        self.check_pass(cmd, "Failed to display MD device details")
        cmd = "mdadm --manage %s --add %s" % (self.raid, self.remadd)
        self.check_pass(cmd, "Failed to add back the drive to MD device")
        cmd = "mdadm --detail %s" % self.raid
        self.check_pass(cmd, "Failed to display MD device details")
        cmd = "mdadm --manage %s --stop" % self.raid
        self.check_pass(cmd, "Failed to stop/remove the MD device")
        cmd = "mdadm --assemble %s %s %s" \
              % (self.raid, self.disk, self.sparedisk)
        self.check_pass(cmd, "Failed to assemble back the MD device")
        cmd = "mdadm --detail %s | grep State | grep recovering" % self.raid
        while process.system(cmd, ignore_status=True, shell=True) == 0:
            time.sleep(30)
        process.system(cmd, ignore_status=True, shell=True)
        cmd = "mdadm --detail %s" % self.raid
        self.check_pass(cmd, "Failed to display the MD device details")

    def check_pass(self, cmd, errmsg):
        """
        Function to check if the cmd is successful or not, if not display
        appropriate message
        """
        if process.system(cmd, ignore_status=True, shell=True) != 0:
            self.fail(errmsg)

    def tearDown(self):
        """
        Stop/Remove the MD device
        """
        if self.cleanup:
            cmd = "mdadm --manage %s --stop" % self.raid
            self.check_pass(cmd, "Failed to stop the MD device")
            cmd = "mdadm --zero-superblock %s %s" % (self.disk, self.sparedisk)
            self.check_pass(cmd, "Failed to remove the MD device")


if __name__ == "__main__":
    main()
