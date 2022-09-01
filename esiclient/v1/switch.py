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

import logging

from osc_lib.command import command
from osc_lib import exceptions
from osc_lib.i18n import _

from esiclient import utils


class ListVLAN(command.Lister):
    """List VLANs"""

    log = logging.getLogger(__name__ + ".ListVLAN")

    def get_parser(self, prog_name):
        parser = super(ListVLAN, self).get_parser(prog_name)
        parser.add_argument(
            "switch",
            metavar="<switch>",
            help=_("Switch"))
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        switch = parsed_args.switch

        ironic_client = self.app.client_manager.baremetal
        neutron_client = self.app.client_manager.network

        ports = list((port for port in ironic_client.port.list(detail=True)
                      if port.local_link_connection.get(
                              'switch_info') == switch))
        networks = list(neutron_client.networks(provider_network_type='vlan'))
        neutron_ports = list(neutron_client.ports())

        data = []
        for network in networks:
            switch_ports = []
            subnet_id = next(iter(network.subnet_ids), None)
            if subnet_id:
                nps = (np for np in neutron_ports
                       if next(iter(np.fixed_ips), None).get(
                               'subnet_id', None) == subnet_id)
                for np in nps:
                    port = next((port for port in ports
                                 if port.internal_info.get(
                                         'tenant_vif_port_id', None) == np.id),
                                None)
                    if port:
                        switch_ports.append(
                            port.local_link_connection.get('port_id'))
            data.append([network.provider_segmentation_id,
                         switch_ports])

        return ["VLAN", "Ports"], data


class EnableAccessPort(command.ShowOne):
    """Configure Switchport Access"""

    log = logging.getLogger(__name__ + ".EnableAccessPort")

    def get_parser(self, prog_name):
        parser = super(EnableAccessPort, self).get_parser(prog_name)
        parser.add_argument(
            "switch",
            metavar="<switch>",
            help=_("Switch"))
        parser.add_argument(
            "switchport",
            metavar="<switchport>",
            help=_("Switchport"))
        parser.add_argument(
            "vlan_id",
            metavar="<vlan_id>",
            help=_("VLAN ID"))

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        switch = parsed_args.switch
        switchport = parsed_args.switchport
        vlan_id = parsed_args.vlan_id

        # get associated port and node
        ironic_client = self.app.client_manager.baremetal
        ports = ironic_client.port.list(detail=True)
        port = next((port for port in ports
                     if port.local_link_connection.get(
                             'port_id') == switchport and
                     port.local_link_connection.get(
                         'switch_info') == switch),
                    None)
        if not port:
            raise exceptions.CommandError("ERROR: Switchport unknown")
        node = ironic_client.node.get(port.node_uuid)

        # get associated network
        neutron_client = self.app.client_manager.network
        networks = list(neutron_client.networks(
            provider_network_type='vlan',
            provider_segmentation_id=vlan_id))
        network = next(iter(networks), None)
        if not network:
            raise exceptions.CommandError("ERROR: VLAN ID unknown")

        # attach node to network
        vif_info = {}
        np_name = utils.get_port_name(network.name, prefix=node.name)
        np = utils.get_or_create_port(np_name, network, neutron_client)
        ironic_client.node.vif_attach(node.uuid, np.id, **vif_info)

        return ["Switchport", "VLAN", "Node", "Network"], \
            [switchport, vlan_id, node.name, network.name]


class DisableAccessPort(command.Command):
    """Disable Switchport Access"""

    log = logging.getLogger(__name__ + ".DisableAccessPort")

    def get_parser(self, prog_name):
        parser = super(DisableAccessPort, self).get_parser(prog_name)
        parser.add_argument(
            "switch",
            metavar="<switch>",
            help=_("Switch"))
        parser.add_argument(
            "switchport",
            metavar="<switchport>",
            help=_("Switchport"))

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        switch = parsed_args.switch
        switchport = parsed_args.switchport

        ironic_client = self.app.client_manager.baremetal
        ports = ironic_client.port.list(detail=True)
        port = next((port for port in ports
                     if port.local_link_connection.get(
                             'port_id') == switchport and
                     port.local_link_connection.get(
                         'switch_info') == switch),
                    None)
        if not port:
            raise exceptions.CommandError("ERROR: Switchport unknown")

        np_uuid = port.internal_info.get('tenant_vif_port_id', None)
        if not np_uuid:
            raise exceptions.CommandError(
                "ERROR: No neutron port found for switchport")

        print("Disabling access to {0}".format(switchport))

        ironic_client.node.vif_detach(port.node_uuid, np_uuid)
