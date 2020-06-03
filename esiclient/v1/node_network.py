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

ACTIVE = 'active'
ADOPT = 'adopt'
MANAGEABLE = 'manageable'


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
        self.log.debug("take_action(%s)" % parsed_args)

        ironic_client = self.app.client_manager.baremetal
        neutron_client = self.app.client_manager.network

        if parsed_args.node:
            ports = ironic_client.port.list(node=parsed_args.node, detail=True)
        else:
            ports = ironic_client.port.list(detail=True)

        if parsed_args.network:
            filter_network = neutron_client.find_network(parsed_args.network)

        data = []
        for port in ports:
            node = ironic_client.node.get(port.node_uuid)
            neutron_port_id = port.internal_info.get('tenant_vif_port_id')
            if neutron_port_id:
                neutron_port = neutron_client.get_port(neutron_port_id)
                network_id = neutron_port.network_id
                if not parsed_args.network or filter_network.id == network_id:
                    names, fixed_ips = utils.get_full_network_info_from_port(
                        neutron_port, neutron_client)
                    data.append([node.name, port.address,
                                 neutron_port.name,
                                 "\n".join(names),
                                 "\n".join(fixed_ips)])
            elif not parsed_args.network:
                data.append([node.name, port.address, None, None, None])

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
            help=_("Attach to this port (name or UUID).")
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)" % parsed_args)

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

        if node.provision_state == MANAGEABLE:
            # adopt the node
            node_update = []
            node_revert = []
            if 'image_source' not in node.instance_info:
                temp_image = node.driver_info['deploy_ramdisk']
                node_update.append({'path': '/instance_info/image_source',
                                    'value': temp_image,
                                    'op': 'add'})
                node_revert.append({'path': '/instance_info/image_source',
                                    'op': 'remove'})
            if 'capabilities' not in node.instance_info:
                node_update.append({'path': '/instance_info/capabilities',
                                    'value': "{\"boot_option\": \"local\"}",
                                    'op': 'add'})
                node_revert.append({'path': '/instance_info/capabilities',
                                    'op': 'remove'})

            try:
                if len(node_update) > 0:
                    ironic_client.node.update(node_uuid, node_update)
                ironic_client.node.set_provision_state(node_uuid, ADOPT)
            finally:
                if len(node_revert) > 0:
                    ironic_client.node.update(node_uuid, node_revert)
            # reload node information
            node = ironic_client.node.get(node_uuid)

        if node.provision_state != ACTIVE:
            raise exceptions.CommandError(
                "ERROR: Node {0} must be in the active state".format(
                    node.name))

        baremetal_ports = ironic_client.port.list(node=node_uuid, detail=True)
        has_free_port = False
        for bp in baremetal_ports:
            if 'tenant_vif_port_id' not in bp.internal_info:
                has_free_port = True
                break

        if not has_free_port:
            raise exceptions.CommandError(
                "ERROR: Node {0} has no free ports".format(node.name))

        if port:
            print("Attaching node {0} to port {1}".format(
                node.name, port.name))
            ironic_client.node.vif_attach(node_uuid, port.id)
            network = neutron_client.get_network(port.network_id)
        else:
            print("Attaching network {1} to node {0}".format(
                node.name, network.name))
            port = neutron_client.create_port(name=node.name,
                                              network_id=network.id)
            ironic_client.node.vif_attach(node_uuid, port.id)
            port = neutron_client.get_port(port.id)

        names, fixed_ips = utils.get_full_network_info_from_port(
            port, neutron_client)

        return ["Node", "MAC Address", "Port", "Network", "Fixed IP"], \
            [node.name, port.mac_address, port.name,
             "\n".join(names),
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
        self.log.debug("take_action(%s)" % parsed_args)

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
