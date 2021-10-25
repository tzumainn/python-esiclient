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
class MetalsmithDeployTests(base.ESIBaseTestClass):
    """Functional tests for metalsmith node deploy commands."""

    @classmethod
    def setUpClass(cls):
        super(MetalsmithDeployTests, cls).setUpClass()

        cls._init_dummy_project(cls, 'random', 'member')

    def setUp(self):
        super(MetalsmithDeployTests, self).setUp()
        self.clients = MetalsmithDeployTests.clients
        self.metalsmith_clients = MetalsmithDeployTests.metalsmith_clients
        self.users = MetalsmithDeployTests.users
        self.projects = MetalsmithDeployTests.projects
        if 'user_image_ident' not in \
                MetalsmithDeployTests.config['functional']:
            self.fail('user_image_ident must be specified in test config')
        self.user_image_ident = MetalsmithDeployTests.\
            config['functional']['user_image_ident']
        self.network = utils.network_create(self.clients['admin'])
        self.addCleanup(utils.network_delete,
                        self.clients['admin'],
                        self.network['name'])

    def test_non_owner_lessee_cannot_deploy_node_metalsmith(self):
        """Tests non owner/lessee metalsmith node deploy functionality.

        Tests that a project which is not set to a node's 'owner' nor
            'lessee' cannot run `metalsmith deploy <image> <node>`
            Test steps:
            1) Create a node and set the state to 'available'
            2) Check that the project cannot run
               `metalsmith deploy <image> <node>`
            3) (cleanup) Delete the node created in step 1

        """

        node = utils.node_create(self.clients['admin'])
        if node['provision_state'] != 'manageable':
            utils.node_set_provision_state(self.clients['admin'],
                                           node['name'], 'manage')
        utils.node_set_provision_state(self.clients['admin'],
                                       node['name'], 'provide')

        self.addCleanup(utils.node_delete,
                        self.clients['admin'],
                        node['name'])

        self.assertRaises(exceptions.CommandFailed,
                          utils.metalsmith_deploy,
                          self.metalsmith_clients['random-member'],
                          self.user_image_ident, self.network['name'])
