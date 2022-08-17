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
from oslo_utils import uuidutils

from esiclient import utils


class List(command.Lister):
    """List networks attached to node"""

    log = logging.getLogger(__name__ + ".List")

    def get_parser(self, prog_name):
        parser = super(List, self).get_parser(prog_name)
        parser.add_argument(
            '--node',
            dest='node',
            metavar='<node>',
            help=_("Filter by this node (name or UUID).")
        )
        parser.add_argument(
            '--network',
            dest='network',
            metavar='<network>',
            help=_("Filter by this network (name or UUID).")
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        ironic_client = self.app.client_manager.baremetal
        neutron_client = self.app.client_manager.network

        if parsed_args.node:
            ports = ironic_client.port.list(node=parsed_args.node, detail=True)
            if uuidutils.is_uuid_like(parsed_args.node):
                node_name = ironic_client.node.get(parsed_args.node).name
            else:
                node_name = parsed_args.node
        else:
            ports = ironic_client.port.list(detail=True)
            nodes = ironic_client.node.list()

        filter_network = None
        if parsed_args.network:
            filter_network = neutron_client.find_network(parsed_args.network)
            neutron_ports = list(neutron_client.ports(
                network_id=filter_network.id))
        else:
            networks = list(neutron_client.networks())
            neutron_ports = list(neutron_client.ports())

        data = []

        for port in ports:
            if not parsed_args.node:
                node_name = next((node for node in nodes
                                  if node.uuid == port.node_uuid), None).name

            neutron_port_id = port.internal_info.get('tenant_vif_port_id')
            neutron_port = None

            if neutron_port_id:
                neutron_port = next((np for np in neutron_ports
                                     if np.id == neutron_port_id), None)

            if neutron_port is not None:
                network_id = neutron_port.network_id

                if not filter_network or filter_network.id == network_id:
                    if filter_network:
                        network = filter_network
                    else:
                        network = next((network for network in networks
                                        if network.id == network_id), None)

                    network_name = utils.get_network_display_name(network)
                    fixed_ip = ''
                    if neutron_port.fixed_ips and \
                            len(neutron_port.fixed_ips) > 0:
                        fixed_ip = neutron_port.fixed_ips[0]['ip_address']
                        data.append([node_name, port.address,
                                    neutron_port.name,
                                    network_name,
                                    fixed_ip])
            elif not filter_network:
                data.append([node_name, port.address, None, None, None])

        return ["Node", "MAC Address", "Port", "Network", "Fixed IP"], data


class Attach(command.ShowOne):
    """Attach network to node"""

    log = logging.getLogger(__name__ + ".Attach")

    def get_parser(self, prog_name):
        parser = super(Attach, self).get_parser(prog_name)
        parser.add_argument(
            "node",
            metavar="<node>",
            help=_("Name or UUID of the node"))
        parser.add_argument(
            "--network",
            metavar="<network>",
            help=_("Name or UUID of the network"))
        parser.add_argument(
            '--port',
            dest='port',
            metavar='<port>',
            help=_("Attach to this neutron port (name or UUID).")
        )
        parser.add_argument(
            '--mac-address',
            dest='mac_address',
            metavar='<mac address>',
            help=_("Attach to this mac address.")
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        node_uuid = parsed_args.node
        if parsed_args.network and parsed_args.port:
            raise exceptions.CommandError(
                "ERROR: Specify only one of network or port")
        if not parsed_args.network and not parsed_args.port:
            raise exceptions.CommandError(
                "ERROR: You must specify either network or port")

        ironic_client = self.app.client_manager.baremetal
        neutron_client = self.app.client_manager.network

        if parsed_args.network:
            network = neutron_client.find_network(parsed_args.network)
            port = None
        elif parsed_args.port:
            port = neutron_client.find_port(parsed_args.port)

        node = ironic_client.node.get(node_uuid)

        if parsed_args.mac_address:
            bp = ironic_client.port.get_by_address(parsed_args.mac_address)
            vif_info = {'port_uuid': bp.uuid}
            mac_string = " on {0}".format(parsed_args.mac_address)
        else:
            vif_info = {}
            mac_string = ""

            baremetal_ports = ironic_client.port.list(
                node=node_uuid, detail=True)
            has_free_port = False
            for bp in baremetal_ports:
                if 'tenant_vif_port_id' not in bp.internal_info:
                    has_free_port = True
                    break

            if not has_free_port:
                raise exceptions.CommandError(
                    "ERROR: Node {0} has no free ports".format(node.name))

        if port:
            print("Attaching port {1} to node {0}{2}".format(
                node.name, port.name, mac_string))
            ironic_client.node.vif_attach(node_uuid, port.id, **vif_info)
        else:
            print("Attaching network {1} to node {0}{2}".format(
                node.name, network.name, mac_string))
            port_name = utils.get_port_name(network.name, prefix=node.name)
            port = utils.get_or_create_port(port_name, network, neutron_client)
            ironic_client.node.vif_attach(node_uuid, port.id, **vif_info)
            port = neutron_client.get_port(port.id)

        network_names, _, fixed_ips \
            = utils.get_full_network_info_from_port(
                port, neutron_client)

        return ["Node", "MAC Address", "Port", "Network", "Fixed IP"], \
            [node.name, port.mac_address, port.name,
             "\n".join(network_names),
             "\n".join(fixed_ips)]


class Detach(command.Command):
    """Detach network from node"""

    log = logging.getLogger(__name__ + ".Detach")

    def get_parser(self, prog_name):
        parser = super(Detach, self).get_parser(prog_name)
        parser.add_argument(
            "node",
            metavar="<node>",
            help=_("Name or UUID of the node"))
        parser.add_argument(
            "port",
            metavar="<port>",
            help=_("Name or UUID of the port"))

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        node_uuid = parsed_args.node
        port_uuid = parsed_args.port

        ironic_client = self.app.client_manager.baremetal
        neutron_client = self.app.client_manager.network

        node = ironic_client.node.get(node_uuid)
        port = neutron_client.find_port(port_uuid)

        if not port:
            raise exceptions.CommandError(
                "ERROR: Port {1} not attached to node {0}".format(
                    node.name, port_uuid))

        print("Detaching node {0} from port {1}".format(
            node.name, port.name))

        ironic_client.node.vif_detach(node_uuid, port.id)
