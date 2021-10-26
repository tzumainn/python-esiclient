#    Copyright (c) 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ddt
from tempest.lib import exceptions

from esiclient.tests.functional import base
from esiclient.tests.functional import utils


@ddt.ddt
class NodeVolumeAttachTests(base.ESIBaseTestClass):
    """Functional tests for esi node volume attach commands."""

    @classmethod
    def setUpClass(cls):
        super(NodeVolumeAttachTests, cls).setUpClass()

        cls._init_dummy_project(cls, 'random', 'member')
        cls._init_dummy_project(cls, 'project1', 'member')
        cls._init_dummy_project(cls, 'project2', 'member')

    def setUp(self):
        super(NodeVolumeAttachTests, self).setUp()
        self.clients = NodeVolumeAttachTests.clients
        self.users = NodeVolumeAttachTests.users
        self.projects = NodeVolumeAttachTests.projects
        self.network = utils.network_create(self.clients['admin'])
        self.addCleanup(utils.network_delete,
                        self.clients['admin'],
                        self.network['name'])

    def test_non_owner_lessee_cannot_attach_volume(self):
        """Tests non owner and non lessee node volume attach functionality.

        Tests that a project which is not set to a node's 'owner' nor
            'lessee' cannot run `esi node volume attach`
            Test steps:
            1) Create a node and set the state to 'available'
            2) A random project creates a volume
            3) Check that the project cannot run
               `esi node volume attach --network <network> <node> <volume>`
            4) (cleanup) Delete the node created in step 1
            5) (cleanup) Delete the volume created in step 2

        """

        node = utils.node_create(self.clients['admin'])
        if node['provision_state'] != 'manageable':
            utils.node_set_provision_state(self.clients['admin'],
                                           node['name'], 'manage')
        utils.node_set_provision_state(self.clients['admin'],
                                       node['name'], 'provide')
        volume = utils.volume_create(self.clients['random-member'])
        self.addCleanup(utils.node_delete,
                        self.clients['admin'],
                        node['name'])
        self.addCleanup(utils.volume_delete,
                        self.clients['admin'],
                        volume['id'])
        self.assertRaises(exceptions.CommandFailed,
                          utils.esi_node_volume_attach,
                          self.clients['random-member'],
                          self.network['name'], node['name'],
                          volume['name'])

    def test_owner_volume_no_access_cannot_attach_volume(self):
        """Tests no volume access node volume attach functionality.

        Tests that an owner with no access to the volume
            cannot run `esi node volume attach`
            Test steps:
            1) Create a node and set the state to 'available'
            2) Set project1 to the owner of the node
            3) Project2 creates a private volume
            4) Check that project1 cannot run
               `esi node volume attach --network <network> <node> <volume>`
            5) (cleanup) Delete the node created in step 1
            6) (cleanup) Delete the volume created in step 2

        """

        node = utils.node_create(self.clients['admin'])
        utils.node_set(self.clients['admin'],
                       node['name'],
                       'owner',
                       self.projects['project1']['id'])
        if node['provision_state'] != 'manageable':
            utils.node_set_provision_state(self.clients['admin'],
                                           node['name'], 'manage')
        utils.node_set_provision_state(self.clients['admin'],
                                       node['name'], 'provide')
        volume = utils.volume_create(self.clients['project2-member'])
        self.addCleanup(utils.node_delete,
                        self.clients['admin'],
                        node['name'])
        self.addCleanup(utils.volume_delete,
                        self.clients['admin'],
                        volume['id'])
        self.assertRaises(exceptions.CommandFailed,
                          utils.esi_node_volume_attach,
                          self.clients['project1-member'],
                          self.network['name'], node['name'],
                          volume['name'])

    def test_lessee_volume_no_access_cannot_attach_volume(self):
        """Tests no volume access node volume attach functionality.

        Tests that a lessee with no access to the volume
            cannot run `esi node volume attach`
            Test steps:
            1) Create a node and set the state to 'available'
            2) Set project1 to the lessee of the node
            3) Project2 creates a private volume
            4) Check that project1 cannot run
               `esi node volume attach --network <network> <node> <volume>`
            5) (cleanup) Delete the node created in step 1
            6) (cleanup) Delete the volume created in step 2

        """

        node = utils.node_create(self.clients['admin'])
        utils.node_set(self.clients['admin'],
                       node['name'],
                       'lessee',
                       self.projects['project1']['id'])
        if node['provision_state'] != 'manageable':
            utils.node_set_provision_state(self.clients['admin'],
                                           node['name'], 'manage')
        utils.node_set_provision_state(self.clients['admin'],
                                       node['name'], 'provide')
        volume = utils.volume_create(self.clients['project2-member'])
        self.addCleanup(utils.node_delete,
                        self.clients['admin'],
                        node['name'])
        self.addCleanup(utils.volume_delete,
                        self.clients['admin'],
                        volume['id'])
        self.assertRaises(exceptions.CommandFailed,
                          utils.esi_node_volume_attach,
                          self.clients['project1-member'],
                          self.network['name'], node['name'],
                          volume['name'])
