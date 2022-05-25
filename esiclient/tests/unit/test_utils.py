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
from unittest import TestCase

from esiclient.tests.unit import utils as test_utils
from esiclient import utils


class TestGetNetworkDisplayName(TestCase):

    def test_get_network_display_name(self):
        network = test_utils.create_mock_object({
            "id": "network_uuid",
            "name": "test_network",
            "provider_segmentation_id": "777"
        })

        results = utils.get_network_display_name(network)
        self.assertEqual('test_network (777)', results)

    def test_get_network_display_name_no_segmentation_id(self):
        network = test_utils.create_mock_object({
            "id": "network_uuid",
            "name": "test_network"
        })

        results = utils.get_network_display_name(network)
        self.assertEqual('test_network', results)


class TestGetNetworkInfoFromPort(TestCase):

    def setUp(self):
        super(TestGetNetworkInfoFromPort, self).setUp()
        self.network = test_utils.create_mock_object({
            "id": "network_uuid",
            "name": "test_network",
            "provider_segmentation_id": "777"
        })

        self.neutron_client = mock.Mock()
        self.neutron_client.get_network.return_value = self.network

    def test_get_network_info_from_port(self):
        port = test_utils.create_mock_object({
            "id": "port_uuid",
            "name": "test_port",
            "network_id": "network_uuid",
            "fixed_ips": [{"ip_address": '11.22.33.44'}]
        })

        results = utils.get_network_info_from_port(port, self.neutron_client)
        self.assertEqual(('test_network (777)', '11.22.33.44'), results)

    def test_get_network_info_from_port_no_fixed_ips(self):
        port = test_utils.create_mock_object({
            "id": "port_uuid",
            "name": "test_port",
            "network_id": "network_uuid",
            "fixed_ips": None
        })

        results = utils.get_network_info_from_port(port, self.neutron_client)
        self.assertEqual(('test_network (777)', ''), results)


class TestGetFullNetworkInfoFromPort(TestCase):

    def setUp(self):
        super(TestGetFullNetworkInfoFromPort, self).setUp()
        self.network1 = test_utils.create_mock_object({
            "id": "network_uuid_1",
            "name": "test_network",
            "provider_segmentation_id": "777"
        })
        self.network2 = test_utils.create_mock_object({
            "id": "network_uuid_2",
            "name": "test_network_2",
            "provider_segmentation_id": "888"
        })
        self.subport1 = test_utils.create_mock_object({
            "id": "subport_uuid_1",
            "name": "test_subport_1",
            "network_id": "network_uuid_1",
            "fixed_ips": [{"ip_address": '11.22.33.44'}]
        })
        self.subport2 = test_utils.create_mock_object({
            "id": "subport_uuid_2",
            "name": "test_subport_2",
            "network_id": "network_uuid_2",
            "fixed_ips": [{"ip_address": '55.66.77.88'}]
        })

        self.neutron_client = mock.Mock()

        def mock_network_get(network_uuid):
            if network_uuid == "network_uuid_1":
                return self.network1
            elif network_uuid == "network_uuid_2":
                return self.network2
            return None
        self.neutron_client.get_network.side_effect = mock_network_get

        def mock_port_get(port_uuid):
            if port_uuid == "subport_uuid_1":
                return self.subport1
            elif port_uuid == "subport_uuid_2":
                return self.subport2
            return None
        self.neutron_client.get_port.side_effect = mock_port_get

    def test_get_full_network_info_from_port(self):
        port = test_utils.create_mock_object({
            "id": "port_uuid",
            "name": "test_port",
            "network_id": "network_uuid_1",
            "fixed_ips": [{"ip_address": '77.77.77.77'}],
            "trunk_details": {
                "trunk_id": "trunk_uuid",
                "sub_ports": [
                    {"segmentation_id": "777", "port_id": "subport_uuid_1"},
                    {"segmentation_id": "888", "port_id": "subport_uuid_2"},
                ]
            }
        })

        results = utils.get_full_network_info_from_port(port,
                                                        self.neutron_client)
        self.assertEqual((
            ['test_network (777)', 'test_network (777)',
             'test_network_2 (888)'],
            ['test_port', 'test_subport_1', 'test_subport_2'],
            ['77.77.77.77', '11.22.33.44', '55.66.77.88']
        ), results)

    def test_get_full_network_info_from_port_no_trunk(self):
        port = test_utils.create_mock_object({
            "id": "port_uuid",
            "name": "test_port",
            "network_id": "network_uuid_1",
            "fixed_ips": [{"ip_address": '77.77.77.77'}],
            "trunk_details": None
        })

        results = utils.get_full_network_info_from_port(port,
                                                        self.neutron_client)
        self.assertEqual(
            (['test_network (777)'], ['test_port'], ['77.77.77.77']),
            results
        )


class TestGetPortName(TestCase):

    def setUp(self):
        super(TestGetPortName, self).setUp()
        self.network = test_utils.create_mock_object({
            "id": "network_uuid",
            "name": "test_network",
            "provider_segmentation_id": "777"
        })

    def test_get_port_name(self):
        name = utils.get_port_name(self.network.name)
        self.assertEqual('esi-test_network', name)

    def test_get_port_name_prefix(self):
        name = utils.get_port_name(self.network.name, prefix='foo')
        self.assertEqual('esi-foo-test_network', name)

    def test_get_port_name_suffix(self):
        name = utils.get_port_name(self.network.name, suffix='bar')
        self.assertEqual('esi-test_network-bar', name)

    def test_get_port_name_prefix_and_suffix(self):
        name = utils.get_port_name(self.network.name, prefix='foo',
                                   suffix='bar')
        self.assertEqual('esi-foo-test_network-bar', name)


class TestGetOrCreatePort(TestCase):

    def setUp(self):
        super(TestGetOrCreatePort, self).setUp()
        self.port_name = 'test_port'
        self.network = test_utils.create_mock_object({
            "id": "network_uuid",
            "name": "test_network",
            "provider_segmentation_id": "777"
        })
        self.port = test_utils.create_mock_object({
            "id": "port_uuid",
            "name": self.port_name,
            "status": "DOWN"
        })

        self.neutron_client = mock.Mock()
        self.neutron_client.create_port.return_value = None

    def test_get_or_create_port_no_match(self):
        self.neutron_client.ports.return_value = []

        utils.get_or_create_port(self.port_name, self.network,
                                 self.neutron_client)
        self.neutron_client.create_port.\
            assert_called_once_with(name=self.port_name,
                                    network_id=self.network.id,
                                    device_owner='baremetal:none')

    def test_get_or_create_port_one_match(self):
        self.neutron_client.ports.return_value = [self.port]

        utils.get_or_create_port(self.port_name, self.network,
                                 self.neutron_client)
        self.neutron_client.create_port.assert_not_called()

    def test_get_or_create_port_many_matches(self):
        self.neutron_client.ports.return_value = [self.port, self.port]

        utils.get_or_create_port(self.port_name, self.network,
                                 self.neutron_client)
        self.neutron_client.create_port.assert_not_called()
