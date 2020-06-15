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
    names = []
    fixed_ips = []

    name, fixed_ip = get_network_info_from_port(port, client)
    names.append(name)
    fixed_ips.append(fixed_ip)

    if port.trunk_details:
        subports = port.trunk_details['sub_ports']
        for subport_info in subports:
            subport = client.get_port(subport_info['port_id'])
            name, fixed_ip = get_network_info_from_port(subport, client)
            names.append(name)
            fixed_ips.append(fixed_ip)

    return names, fixed_ips
