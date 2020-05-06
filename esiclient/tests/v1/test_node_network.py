#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

from osc_lib import exceptions

from esiclient.tests import base
from esiclient.tests import utils
from esiclient.v1 import node_network


class TestList(base.TestCommand):

    def setUp(self):
        super(TestList, self).setUp()
        self.cmd = node_network.List(self.app, None)

        self.port1 = utils.create_mock_object({
            "uuid": "port_uuid_1",
            "node_uuid": "node_uuid_1",
            "address": "aa:aa:aa:aa:aa:aa",
            "internal_info": {'tenant_vif_port_id': 'neutron_port_uuid_1'}
        })
        self.port2 = utils.create_mock_object({
            "uuid": "port_uuid_2",
            "node_uuid": "node_uuid_2",
            "address": "bb:bb:bb:bb:bb:bb",
            "internal_info": {}
        })
        self.port3 = utils.create_mock_object({
            "uuid": "port_uuid_3",
            "node_uuid": "node_uuid_2",
            "address": "cc:cc:cc:cc:cc:cc",
            "internal_info": {'tenant_vif_port_id': 'neutron_port_uuid_2'}
        })
        self.node1 = utils.create_mock_object({
            "uuid": "node_uuid_1",
            "name": "node1"
        })
        self.node2 = utils.create_mock_object({
            "uuid": "node_uuid_2",
            "name": "node2"
        })
        self.network = utils.create_mock_object({
            "id": "network_uuid",
            "name": "test_network"
        })
        self.neutron_port1 = utils.create_mock_object({
            "id": "neutron_port_uuid_1",
            "network_id": "network_uuid",
            "name": "node1",
            "fixed_ips": [{"ip_address": "1.1.1.1"}]
        })
        self.neutron_port2 = utils.create_mock_object({
            "id": "neutron_port_uuid_2",
            "network_id": "network_uuid",
            "name": "node2",
            "fixed_ips": [{"ip_address": "2.2.2.2"}]
        })

        def mock_node_get(node_uuid):
            if node_uuid == "node_uuid_1":
                return self.node1
            elif node_uuid == "node_uuid_2":
                return self.node2
            return None
        self.app.client_manager.baremetal.node.get.side_effect = mock_node_get

        def mock_neutron_port_get(port_uuid):
            if port_uuid == "neutron_port_uuid_1":
                return self.neutron_port1
            elif port_uuid == "neutron_port_uuid_2":
                return self.neutron_port2
            return None

        self.app.client_manager.network.get_port.\
            side_effect = mock_neutron_port_get
        self.app.client_manager.network.find_network.\
            return_value = self.network
        self.app.client_manager.network.get_network.\
            return_value = self.network

    def test_take_action(self):
        self.app.client_manager.baremetal.port.list.\
            return_value = [self.port1, self.port2, self.port3]

        arglist = []
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        results = self.cmd.take_action(parsed_args)
        expected = (
            ["Node", "MAC Address", "Network", "Fixed IP"],
            [["node1", "aa:aa:aa:aa:aa:aa", "test_network", "1.1.1.1"],
             ["node2", "bb:bb:bb:bb:bb:bb", None, None],
             ["node2", "cc:cc:cc:cc:cc:cc", "test_network", "2.2.2.2"]]
        )
        self.assertEqual(expected, results)
        self.app.client_manager.baremetal.port.list.\
            assert_called_once_with(detail=True)

    def test_take_action_node_filter(self):
        self.app.client_manager.baremetal.port.list.\
            return_value = [self.port2, self.port3]

        arglist = ['--node', 'node2']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        results = self.cmd.take_action(parsed_args)
        expected = (
            ["Node", "MAC Address", "Network", "Fixed IP"],
            [["node2", "bb:bb:bb:bb:bb:bb", None, None],
             ["node2", "cc:cc:cc:cc:cc:cc", "test_network", "2.2.2.2"]]
        )
        self.assertEqual(expected, results)
        self.app.client_manager.baremetal.port.list.\
            assert_called_once_with(node="node2", detail=True)

    def test_take_action_network_filter(self):
        self.app.client_manager.baremetal.port.list.\
            return_value = [self.port1, self.port2, self.port3]

        arglist = ['--network', 'network']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        results = self.cmd.take_action(parsed_args)
        expected = (
            ["Node", "MAC Address", "Network", "Fixed IP"],
            [["node1", "aa:aa:aa:aa:aa:aa", "test_network", "1.1.1.1"],
             ["node2", "cc:cc:cc:cc:cc:cc", "test_network", "2.2.2.2"]]
        )
        self.assertEqual(expected, results)
        self.app.client_manager.baremetal.port.list.\
            assert_called_once_with(detail=True)

    def test_take_action_node_network_filter(self):
        self.app.client_manager.baremetal.port.list.\
            return_value = [self.port2, self.port3]

        arglist = ['--node', 'node2', '--network', 'network']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        results = self.cmd.take_action(parsed_args)
        expected = (
            ["Node", "MAC Address", "Network", "Fixed IP"],
            [["node2", "cc:cc:cc:cc:cc:cc", "test_network", "2.2.2.2"]]
        )
        self.assertEqual(expected, results)
        self.app.client_manager.baremetal.port.list.\
            assert_called_once_with(node="node2", detail=True)


class TestAttach(base.TestCommand):

    def setUp(self):
        super(TestAttach, self).setUp()
        self.cmd = node_network.Attach(self.app, None)

        self.port1 = utils.create_mock_object({
            "uuid": "port_uuid_1",
            "node_uuid": "node_uuid_1",
            "address": "aa:aa:aa:aa:aa:aa",
            "internal_info": {'tenant_vif_port_id': 'neutron_port_uuid_1'}
        })
        self.port2 = utils.create_mock_object({
            "uuid": "port_uuid_2",
            "node_uuid": "node_uuid_1",
            "address": "bb:bb:bb:bb:bb:bb",
            "internal_info": {}
        })
        self.node = utils.create_mock_object({
            "uuid": "node_uuid_1",
            "name": "node1",
            "provision_state": "active"
        })
        self.node_available = utils.create_mock_object({
            "uuid": "node_uuid_1",
            "name": "node1",
            "provision_state": "available"
        })
        self.node_manageable = utils.create_mock_object({
            "uuid": "node_uuid_1",
            "name": "node1",
            "provision_state": "manageable",
            "instance_info": {},
            "driver_info": {'deploy_ramdisk': 'fake-image'},
        })
        self.node_manageable_instance_info = utils.create_mock_object({
            "uuid": "node_uuid_1",
            "name": "node1",
            "provision_state": "manageable",
            "instance_info": {'image_source': 'fake-image',
                              'capabilities': {}},
            "driver_info": {'deploy_ramdisk': 'fake-image'},
        })
        self.network = utils.create_mock_object({
            "id": "network_uuid",
            "name": "test_network"
        })
        self.neutron_port = utils.create_mock_object({
            "id": "neutron_port_uuid_2",
            "network_id": "network_uuid",
            "name": "node1",
            "mac_address": "bb:bb:bb:bb:bb:bb",
            "fixed_ips": [{"ip_address": "2.2.2.2"}]
        })

        self.app.client_manager.network.find_network.\
            return_value = self.network
        self.app.client_manager.network.create_port.\
            return_value = self.neutron_port
        self.app.client_manager.network.get_port.\
            return_value = self.neutron_port

    def test_take_action(self):
        self.app.client_manager.baremetal.node.get.\
            return_value = self.node
        self.app.client_manager.baremetal.port.list.\
            return_value = [self.port1, self.port2]

        arglist = ['node1', 'test_network']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        results = self.cmd.take_action(parsed_args)
        expected = (
            ["Node", "MAC Address", "Network", "Fixed IP"],
            ["node1", "bb:bb:bb:bb:bb:bb", "test_network", "2.2.2.2"]
        )
        self.assertEqual(expected, results)
        self.app.client_manager.network.create_port.\
            assert_called_once_with(name=self.node.name,
                                    network_id=self.network.id)
        self.app.client_manager.baremetal.node.vif_attach.\
            assert_called_once_with('node1', self.neutron_port.id)

    def test_take_action_adopt(self):
        self.app.client_manager.baremetal.node.get.\
            return_value = self.node_manageable
        self.app.client_manager.baremetal.port.list.\
            return_value = [self.port1, self.port2]

        def mock_node_set_provision_state(node_uuid, state):
            self.node_manageable.provision_state = "active"

        self.app.client_manager.baremetal.node.set_provision_state.\
            side_effect = mock_node_set_provision_state

        arglist = ['node1', 'test_network']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        results = self.cmd.take_action(parsed_args)
        expected = (
            ["Node", "MAC Address", "Network", "Fixed IP"],
            ["node1", "bb:bb:bb:bb:bb:bb", "test_network", "2.2.2.2"]
        )
        self.assertEqual(expected, results)
        self.app.client_manager.network.create_port.\
            assert_called_once_with(name=self.node.name,
                                    network_id=self.network.id)
        self.app.client_manager.baremetal.node.vif_attach.\
            assert_called_once_with('node1', self.neutron_port.id)
        self.app.client_manager.baremetal.node.vif_attach.\
            assert_called_once_with('node1', self.neutron_port.id)
        self.app.client_manager.baremetal.node.set_provision_state.\
            assert_called_once_with('node1', 'adopt')
        self.assertEqual(
            self.app.client_manager.baremetal.node.update.call_count, 2)

    def test_take_action_adopt_no_update(self):
        self.app.client_manager.baremetal.node.get.\
            return_value = self.node_manageable_instance_info
        self.app.client_manager.baremetal.port.list.\
            return_value = [self.port1, self.port2]

        def mock_node_set_provision_state(node_uuid, state):
            self.node_manageable_instance_info.provision_state = "active"

        self.app.client_manager.baremetal.node.set_provision_state.\
            side_effect = mock_node_set_provision_state

        arglist = ['node1', 'test_network']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        results = self.cmd.take_action(parsed_args)
        expected = (
            ["Node", "MAC Address", "Network", "Fixed IP"],
            ["node1", "bb:bb:bb:bb:bb:bb", "test_network", "2.2.2.2"]
        )
        self.assertEqual(expected, results)
        self.app.client_manager.network.create_port.\
            assert_called_once_with(name=self.node.name,
                                    network_id=self.network.id)
        self.app.client_manager.baremetal.node.vif_attach.\
            assert_called_once_with('node1', self.neutron_port.id)
        self.app.client_manager.baremetal.node.vif_attach.\
            assert_called_once_with('node1', self.neutron_port.id)
        self.app.client_manager.baremetal.node.set_provision_state.\
            assert_called_once_with('node1', 'adopt')
        self.assertEqual(
            self.app.client_manager.baremetal.node.update.call_count, 0)

    def test_take_action_node_state_exception(self):
        self.app.client_manager.baremetal.node.get.\
            return_value = self.node_available
        self.app.client_manager.baremetal.port.list.\
            return_value = [self.port1, self.port2]

        arglist = ['node1', 'test_network']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.assertRaisesRegex(
            exceptions.CommandError,
            'ERROR: Node node1 must be in the active state',
            self.cmd.take_action, parsed_args)

    def test_take_action_port_free_exception(self):
        self.app.client_manager.baremetal.node.get.\
            return_value = self.node
        self.app.client_manager.baremetal.port.list.\
            return_value = [self.port1]

        arglist = ['node1', 'test_network']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.assertRaisesRegex(
            exceptions.CommandError,
            'ERROR: Node node1 has no free ports',
            self.cmd.take_action, parsed_args)


class TestDetach(base.TestCommand):

    def setUp(self):
        super(TestDetach, self).setUp()
        self.cmd = node_network.Detach(self.app, None)

        self.node = utils.create_mock_object({
            "uuid": "node_uuid_1",
            "name": "node1",
            "provision_state": "active"
        })
        self.network = utils.create_mock_object({
            "id": "network_uuid",
            "name": "test_network"
        })
        self.neutron_port = utils.create_mock_object({
            "id": "neutron_port_uuid_1",
            "network_id": "network_uuid",
            "name": "node1",
            "mac_address": "bb:bb:bb:bb:bb:bb",
            "fixed_ips": [{"ip_address": "2.2.2.2"}]
        })

        self.app.client_manager.baremetal.node.get.\
            return_value = self.node
        self.app.client_manager.network.find_network.\
            return_value = self.network

    def test_take_action(self):
        self.app.client_manager.network.find_port.\
            return_value = self.neutron_port

        arglist = ['node1', 'test_network']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.cmd.take_action(parsed_args)
        self.app.client_manager.baremetal.node.vif_detach.\
            assert_called_once_with('node1', self.neutron_port.id)
        self.app.client_manager.network.delete_port.\
            assert_called_once_with(self.neutron_port.id)

    def test_take_action_port_exception(self):
        self.app.client_manager.network.find_port.\
            return_value = None

        arglist = ['node1', 'test_network']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.assertRaisesRegex(
            exceptions.CommandError,
            'ERROR: Network test_network is not attached to node node1',
            self.cmd.take_action, parsed_args
        )
