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

import mock
from mock import call
from mock import patch

from esiclient.tests.unit import base
from esiclient.tests.unit import utils
from esiclient.v1.orchestrator import cluster


class TestOrchestrate(base.TestCommand):

    def setUp(self):
        super(TestOrchestrate, self).setUp()
        self.cmd = cluster.Orchestrate(self.app, None)

        self.node1 = utils.create_mock_object({
            "uuid": "node_uuid_1",
            "name": "node1",
            "provision_state": "available",
            "resource_class": "baremetal"
        })
        self.node2 = utils.create_mock_object({
            "uuid": "node_uuid_2",
            "name": "node2",
            "provision_state": "available",
            "resource_class": "baremetal"
        })
        self.node3 = utils.create_mock_object({
            "uuid": "node_uuid_3",
            "name": "node3",
            "provision_state": "available",
            "resource_class": "baremetal"
        })
        self.port1 = utils.create_mock_object({
            "id": "port_uuid_1",
            "name": "port1",
            "network_id": "network_uuid_1",
        })
        self.port2 = utils.create_mock_object({
            "id": "port_uuid_2",
            "name": "port2",
            "network_id": "network_uuid_1",
        })
        self.port3 = utils.create_mock_object({
            "id": "port_uuid_3",
            "name": "port3",
            "network_id": "network_uuid_1",
        })
        self.private_network = utils.create_mock_object({
            "id": "network_uuid_1",
            "name": "private_network_1",
        })
        self.external_network = utils.create_mock_object({
            "id": "network_uuid_3",
            "name": "external_network",
        })
        self.image = utils.create_mock_object({
            "id": "image_uuid_1",
            "name": "image",
        })

        def mock_find_network(name):
            if name == "private_network_1":
                return self.private_network
            if name == "external_network":
                return self.external_network
            return None
        self.app.client_manager.network.find_network.\
            side_effect = mock_find_network
        self.app.client_manager.baremetal.node.list.return_value = [
            self.node1, self.node2, self.node3]
        self.app.client_manager.network.ips.return_value = []
        self.app.client_manager.network.networks.return_value = []
        self.app.client_manager.network.find_port.return_value = self.port1
        self.app.client_manager.image.find_image.return_value = self.image

    @mock.patch(
        'esiclient.utils.get_floating_ip',
        autospec=True)
    @mock.patch(
        'esiclient.utils.get_full_network_info_from_port',
        autospec=True)
    @mock.patch(
        'esiclient.utils.get_or_assign_port_floating_ip',
        autospec=True)
    @mock.patch(
        'esiclient.utils.boot_node_from_url',
        autospec=True)
    @mock.patch(
        'esiclient.utils.provision_node_with_image',
        autospec=True)
    @mock.patch(
        'esiclient.utils.get_or_create_port',
        autospec=True)
    @mock.patch(
        'esiclient.utils.create_trunk',
        autospec=True)
    @mock.patch('json.load', autospec=True)
    def test_take_action(self, mock_load, mock_ct, mock_gocp, mock_pnwi,
                         mock_bnfu, mock_goapfi, mock_gfnifp, mock_gfi):
        mock_load.return_value = {
            "node_configs": [
                {
                    "nodes": {
                        "node_uuids": ["node1"]
                    },
                    "network": {
                        "network_uuid": "private_network_1",
                        "tagged_network_uuids": ["private_network_2"],
                        "fip_network_uuid": "external_network"
                    },
                    "provisioning": {
                        "provisioning_type": "image",
                        "image_uuid": "image_uuid",
                        "ssh_key": "/path/to/ssh/key"
                    }
                },
                {
                    "nodes": {
                        "num_nodes": "2",
                        "resource_class": "baremetal"
                    },
                    "network": {
                        "network_uuid": "private_network_1"
                    },
                    "provisioning": {
                        "provisioning_type": "image_url",
                        "url": "https://image.url"
                    }
                }
            ]
        }
        mock_ct.return_value = None, self.port1
        mock_gocp.side_effect = [self.port2, self.port3]
        mock_gfnifp.return_value = [], [], []
        mock_gfi.return_value = [], []

        arglist = ['config.json']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        with patch("builtins.open"):
            self.cmd.take_action(parsed_args)

        self.app.client_manager.baremetal.node.list.assert_called_once_with(
            fields=["uuid", "name", "resource_class"],
            provision_state='available'
        )
        self.app.client_manager.network.find_network.assert_has_calls([
            call('private_network_1'), call('external_network')
        ])
        mock_ct.assert_called_once_with(
            self.app.client_manager.network,
            'esi-node1-trunk', self.private_network, ['private_network_2']
        )
        self.app.client_manager.network.find_port.assert_called_once_with(
            self.port1.id
        )
        mock_gocp.assert_has_calls([
            call('esi-node2-private_network_1', self.private_network,
                 self.app.client_manager.network),
            call('esi-node3-private_network_1', self.private_network,
                 self.app.client_manager.network),
        ])
        mock_pnwi.assert_called_once_with(
            self.node1.uuid, 'baremetal', self.port1.id,
            self.image.id, '/path/to/ssh/key'
        )
        mock_bnfu.assert_has_calls([
            call(self.node2.uuid, 'https://image.url',
                 self.port2.id, self.app.client_manager.baremetal),
            call(self.node3.uuid, 'https://image.url',
                 self.port3.id, self.app.client_manager.baremetal),
        ])
        mock_goapfi.assert_called_once_with(
            self.port1, self.external_network, self.app.client_manager.network
        )
        assert mock_gfnifp.call_count == 3
        assert mock_gfi.call_count == 3

    @mock.patch('json.load', autospec=True)
    def test_take_action_insufficient_nodes(self, mock_load):
        mock_load.return_value = {
            "node_configs": [
                {
                    "nodes": {
                        "node_uuids": ["node1"]
                    },
                    "network": {
                        "network_uuid": "private_network_1",
                        "tagged_network_uuids": ["private_network_2"],
                        "fip_network_uuid": "external_network"
                    },
                    "provisioning": {
                        "provisioning_type": "image",
                        "image_uuid": "image_uuid",
                        "ssh_key": "/path/to/ssh/key"
                    }
                },
                {
                    "nodes": {
                        "num_nodes": "3",
                        "resource_class": "baremetal"
                    },
                    "network": {
                        "network_uuid": "private_network_1"
                    },
                    "provisioning": {
                        "provisioning_type": "image_url",
                        "url": "https://image.url"
                    }
                }
            ]
        }

        arglist = ['config.json']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        with patch("builtins.open"):
            self.assertRaisesRegex(
                cluster.ESIOrchestrationException,
                "Cannot find 3 free baremetal nodes",
                self.cmd.take_action,
                parsed_args)

        self.app.client_manager.baremetal.node.list.assert_called_once_with(
            fields=["uuid", "name", "resource_class"],
            provision_state='available'
        )

    @mock.patch('json.load', autospec=True)
    def test_take_action_unavailable_node(self, mock_load):
        mock_load.return_value = {
            "node_configs": [
                {
                    "nodes": {
                        "node_uuids": ["node5"]
                    },
                    "network": {
                        "network_uuid": "private_network_1",
                        "tagged_network_uuids": ["private_network_2"],
                        "fip_network_uuid": "external_network"
                    },
                    "provisioning": {
                        "provisioning_type": "image",
                        "image_uuid": "image_uuid",
                        "ssh_key": "/path/to/ssh/key"
                    }
                },
                {
                    "nodes": {
                        "num_nodes": "2",
                        "resource_class": "baremetal"
                    },
                    "network": {
                        "network_uuid": "private_network_1"
                    },
                    "provisioning": {
                        "provisioning_type": "image_url",
                        "url": "https://image.url"
                    }
                }
            ]
        }

        arglist = ['config.json']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        with patch("builtins.open"):
            self.assertRaisesRegex(
                cluster.ESIOrchestrationException,
                "node5 is not an available node",
                self.cmd.take_action,
                parsed_args)

        self.app.client_manager.baremetal.node.list.assert_called_once_with(
            fields=["uuid", "name", "resource_class"],
            provision_state='available'
        )

    @mock.patch('json.load', autospec=True)
    def test_take_action_no_network(self, mock_load):
        mock_load.return_value = {
            "node_configs": [
                {
                    "nodes": {
                        "node_uuids": ["node1"]
                    },
                    "network": {
                        "no_network": "",
                        "tagged_network_uuids": ["private_network_2"],
                        "fip_network_uuid": "external_network"
                    },
                    "provisioning": {
                        "provisioning_type": "image",
                        "image_uuid": "image_uuid",
                        "ssh_key": "/path/to/ssh/key"
                    }
                },
                {
                    "nodes": {
                        "num_nodes": "2",
                        "resource_class": "baremetal"
                    },
                    "network": {
                        "no_network": ""
                    },
                    "provisioning": {
                        "provisioning_type": "image_url",
                        "url": "https://image.url"
                    }
                }
            ]
        }

        arglist = ['config.json']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        with patch("builtins.open"):
            self.assertRaisesRegex(
                cluster.ESIOrchestrationException,
                "Must specify a network",
                self.cmd.take_action,
                parsed_args)

        self.app.client_manager.baremetal.node.list.assert_called_once_with(
            fields=["uuid", "name", "resource_class"],
            provision_state='available'
        )

    @mock.patch('json.load', autospec=True)
    def test_take_action_invalid_provisioning_type(self, mock_load):
        mock_load.return_value = {
            "node_configs": [
                {
                    "nodes": {
                        "node_uuids": ["node1"]
                    },
                    "network": {
                        "network_uuid": "private_network_1",
                        "tagged_network_uuids": ["private_network_2"],
                        "fip_network_uuid": "external_network"
                    },
                    "provisioning": {
                        "provisioning_type": "foo",
                        "image_uuid": "image_uuid",
                        "ssh_key": "/path/to/ssh/key"
                    }
                },
                {
                    "nodes": {
                        "num_nodes": "2",
                        "resource_class": "baremetal"
                    },
                    "network": {
                        "network_uuid": "private_network_1"
                    },
                    "provisioning": {
                        "provisioning_type": "bar",
                        "url": "https://image.url"
                    }
                }
            ]
        }

        arglist = ['config.json']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        with patch("builtins.open"):
            self.assertRaisesRegex(
                cluster.ESIOrchestrationException,
                "Unknown provisioning method",
                self.cmd.take_action,
                parsed_args)

        self.app.client_manager.baremetal.node.list.assert_called_once_with(
            fields=["uuid", "name", "resource_class"],
            provision_state='available'
        )


class TestUndeploy(base.TestCommand):

    def setUp(self):
        super(TestUndeploy, self).setUp()
        self.cmd = cluster.Undeploy(self.app, None)

        self.port1 = utils.create_mock_object({
            "id": "port_uuid_1",
            "name": "esi-node2-network2",
            "network_id": "network_uuid_1",
        })
        self.port2 = utils.create_mock_object({
            "id": "port_uuid_2",
            "name": "esi-node3-network2",
            "network_id": "network_uuid_2",
        })
        self.network1 = utils.create_mock_object({
            "id": "network_uuid_1",
            "name": "network1",
        })
        self.network2 = utils.create_mock_object({
            "id": "network_uuid_2",
            "name": "network2",
        })
        self.trunk = utils.create_mock_object({
            "id": "trunk_uuid_1",
            "name": "trunk",
        })

        def mock_find_network(name):
            if name == "network1":
                return self.network1
            if name == "network2":
                return self.network2
            return None
        self.app.client_manager.network.find_network.\
            side_effect = mock_find_network

        def mock_find_port(name):
            if name == "esi-node2-network2":
                return self.port1
            if name == "esi-node3-network2":
                return self.port2
            return None
        self.app.client_manager.network.find_port.\
            side_effect = mock_find_port
        self.app.client_manager.network.delete_port.\
            return_value = None

        self.app.client_manager.network.find_trunk.return_value = \
            self.trunk

        self.app.client_manager.baremetal.node.set_provision_state.\
            return_value = None

    @mock.patch(
        'esiclient.utils.delete_trunk',
        autospec=True)
    @mock.patch('time.sleep', autospec=True)
    @mock.patch('json.load', autospec=True)
    def test_take_action(self, mock_load, mock_sleep, mock_dt):
        mock_load.return_value = {
            "node_configs": [
                {
                    "nodes": {
                        "node_uuids": ["node1"]
                    },
                    "network": {
                        "network_uuid": "network1",
                        "tagged_network_uuids": ["network2"],
                        "fip_network_uuid": "external_network"
                    },
                    "provisioning": {
                        "provisioning_type": "image",
                        "image_uuid": "image_uuid",
                        "ssh_key": "/path/to/ssh/key"
                    }
                },
                {
                    "nodes": {
                        "node_uuids": ["node2", "node3"]
                    },
                    "network": {
                        "network_uuid": "network2"
                    },
                    "provisioning": {
                        "provisioning_type": "image_url",
                        "url": "https://image.url"
                    }
                }
            ]
        }

        arglist = ['config.json']
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        with patch("builtins.open"):
            self.cmd.take_action(parsed_args)

        self.app.client_manager.network.find_network.assert_has_calls([
            call('network1'),
            call('network2')
        ])
        self.app.client_manager.baremetal.node.set_provision_state.\
            assert_has_calls([
                call('node1', 'deleted'),
                call('node2', 'deleted'),
                call('node3', 'deleted')
            ])
        self.app.client_manager.network.find_trunk.\
            assert_called_once_with('esi-node1-trunk')
        mock_dt.assert_called_once_with(
            self.app.client_manager.network, self.trunk)
        self.app.client_manager.network.find_port.assert_has_calls([
            call('esi-node2-network2'),
            call('esi-node3-network2')
        ])
        self.app.client_manager.network.delete_port.assert_has_calls([
            call('port_uuid_1'),
            call('port_uuid_2')
        ])
