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


def get_network_display_name(network):
    """Return Neutron network name with vlan, if any

    :param network: a Neutron network
    """
    try:
        return "{0} ({1})".format(
            network.name, network.provider_segmentation_id)
    except Exception:
        # if user does not have permission to see provider_segmentation_id,
        # just show the name
        return network.name


def get_network_info_from_port(port, client):
    """Return Neutron network name and ips from port

    :param port: a Neutron port
    :param client: neutron client
    """
    network = client.get_network(port.network_id)
    fixed_ip = ''
    if port.fixed_ips and len(port.fixed_ips) > 0:
        fixed_ip = port.fixed_ips[0]['ip_address']

    return get_network_display_name(network), fixed_ip


def get_full_network_info_from_port(port, client):
    """Return full Neutron network name and ips from port

    This code iterates through subports if appropriate

    :param port: a Neutron port
    :param client: neutron client
    """
    network_names = []
    port_names = []
    fixed_ips = []

    network_name, fixed_ip = get_network_info_from_port(port, client)
    network_names.append(network_name)
    fixed_ips.append(fixed_ip)
    port_names.append(port.name)

    if port.trunk_details:
        subports = port.trunk_details['sub_ports']
        for subport_info in subports:
            subport = client.get_port(subport_info['port_id'])
            network_name, fixed_ip = get_network_info_from_port(
                subport, client)
            network_names.append(network_name)
            fixed_ips.append(fixed_ip)
            port_names.append(subport.name)

    return network_names, port_names, fixed_ips


def get_port_name(network_name, prefix=None, suffix=None):
    port_name = network_name
    if prefix:
        port_name = "{0}-{1}".format(prefix, port_name)
    if suffix:
        port_name = "{0}-{1}".format(port_name, suffix)
    port_name = "esi-{0}".format(port_name)
    return port_name


def get_or_create_port(port_name, network, client):
    ports = list(client.ports(name=port_name, status='DOWN'))
    if len(ports) > 0:
        port = ports[0]
    else:
        port = client.create_port(
            name=port_name,
            network_id=network.id,
            device_owner='baremetal:none'
        )
    return port
