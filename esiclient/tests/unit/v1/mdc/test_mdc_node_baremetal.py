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

from unittest import mock
import openstack.baremetal.v1.node
import openstack.connection

from esiclient.tests.unit import base
from esiclient.v1.mdc import mdc_node_baremetal


@mock.patch("esiclient.v1.mdc.mdc_node_baremetal.openstack.connect")
@mock.patch("openstack.config.loader.OpenStackConfig.get_cloud_names")
class TestMDCBaremetalNodeList(base.TestCommand):
    def setUp(self):
        super().setUp()
        self.cmd = mdc_node_baremetal.MDCBaremetalNodeList(self.app, None)
        self.cloud_names = [f"esi{i}" for i in range(1, 4)]
        self.connection = mock.Mock(openstack.connection.Connection, name="test-cloud")

        self.node = {}
        for i in range(1, 5):
            node = self.node[i] = mock.Mock(
                openstack.baremetal.v1.node.Node, name=f"node{i}"
            )
            node.configure_mock(
                id=f"node_uuid_{i}",
                name=f"node{i}",
                instance_id=f"instance_uuid_{i}",
                power_state="off",
                provision_state="active",
                is_maintenance=False,
            )

    def test_take_action_list_all_clouds(self, mock_get_cloud_names, mock_connect):
        self.connection.list_machines.side_effect = [
            [self.node[1]],
            [self.node[2]],
            [self.node[3], self.node[4]],
        ]
        mock_connect.return_value = self.connection
        mock_get_cloud_names.return_value = self.cloud_names

        arglist = []
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        results = self.cmd.take_action(parsed_args)

        expected = (
            [
                "Cloud",
                "UUID",
                "Name",
                "Instance UUID",
                "Power State",
                "Provisioning State",
                "Maintenance",
            ],
            [
                [
                    "esi1",
                    "node_uuid_1",
                    "node1",
                    "instance_uuid_1",
                    "off",
                    "active",
                    False,
                ],
                [
                    "esi2",
                    "node_uuid_2",
                    "node2",
                    "instance_uuid_2",
                    "off",
                    "active",
                    False,
                ],
                [
                    "esi3",
                    "node_uuid_3",
                    "node3",
                    "instance_uuid_3",
                    "off",
                    "active",
                    False,
                ],
                [
                    "esi3",
                    "node_uuid_4",
                    "node4",
                    "instance_uuid_4",
                    "off",
                    "active",
                    False,
                ],
            ],
        )
        self.assertEqual(expected, results)
        mock_get_cloud_names.assert_called_once()
        assert self.connection.list_machines.call_count == 3

    def test_take_action_list_specific_cloud(self, mock_get_cloud_names, mock_connect):
        self.connection.list_machines.side_effect = [
            [self.node[1]],
            [self.node[2]],
            [self.node[3], self.node[4]],
        ]
        mock_connect.return_value = self.connection
        mock_get_cloud_names.return_value = self.cloud_names

        arglist = ["esi1"]
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        results = self.cmd.take_action(parsed_args)
        expected = (
            [
                "Cloud",
                "UUID",
                "Name",
                "Instance UUID",
                "Power State",
                "Provisioning State",
                "Maintenance",
            ],
            [
                [
                    "esi1",
                    "node_uuid_1",
                    "node1",
                    "instance_uuid_1",
                    "off",
                    "active",
                    False,
                ],
            ],
        )
        self.assertEqual(expected, results)
        mock_get_cloud_names.assert_called_once()
        assert self.connection.list_machines.call_count == 1
