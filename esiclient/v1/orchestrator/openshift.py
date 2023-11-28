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

import json
import logging
import os
import requests
import time

from osc_lib.command import command
from osc_lib.i18n import _

from esiclient import utils


BASE_ASSISTED_INSTALLER_URL = \
    'https://api.openshift.com/api/assisted-install/v2/'


def call_assisted_installer_api(url, method, headers={}, data=None):
    full_url = BASE_ASSISTED_INSTALLER_URL + url
    if method == 'post':
        response = requests.post(full_url, headers=headers, json=data)
    elif method == 'get':
        response = requests.get(full_url, headers=headers)
    elif method == 'patch':
        response = requests.patch(full_url, headers=headers, json=data)
    else:
        raise OSAIException(
            'Unknown method used when calling Assisted Installer')
    if response.status_code not in [200, 201, 202, 204]:
        raise OSAIException(
            "Unexpected response from Assisted Installer (%s): %s"
            % (response.status_code, response.reason))
    return response


def wait_for_nodes(infra_env_id, headers, num_nodes, target_status):
    waiting = True
    print("waiting for hosts to reach %s..." % target_status)
    while waiting:
        response = call_assisted_installer_api(
            "infra-envs/%s/hosts" % infra_env_id,
            'get', headers)
        count = 0
        print("* checking hosts")
        for host in response.json():
            status = host.get('status')
            print("  * " + host.get('requested_hostname') + ": " + status)
            if status == target_status:
                count = count + 1
        if count == num_nodes:
            waiting = False
        else:
            time.sleep(30)
    print("... hosts ready")
    return


class OSAIException(Exception):
    pass


class OrchestrationException(Exception):
    pass


class Orchestrate(command.Lister):
    """Orchestrate an OpenShift cluster using the Assisted Installer API"""

    log = logging.getLogger(__name__ + ".Orchestrate")
    REQUIRED_FIELDS = ['nodes', 'cluster_name', 'external_network_name',
                       'private_network_name', 'private_subnet_name',
                       'api_vip', 'ingress_vip', 'openshift_version',
                       'base_dns_domain', 'ssh_public_key']

    def _print_failure_message(self, exception, cluster_config_file,
                               cluster_id=None, infra_env_id=None,
                               message=None):
        flags = ""
        if cluster_id:
            flags = "--cluster-id %s" % cluster_id
            if infra_env_id:
                flags = "%s --infra-env-id %s" % (flags, infra_env_id)
        command = "openstack esi orchestrate openshift %s %s" % \
            (flags, cluster_config_file)
        if message:
            print(message)
        print("* %s" % str(exception))
        if isinstance(exception, OSAIException):
            print("* YOU MAY NEED TO REFRESH YOUR OPENSHIFT API TOKEN")
        print("Run this command to continue installation:")
        print("* %s" % command)
        return

    def get_parser(self, prog_name):
        parser = super(Orchestrate, self).get_parser(prog_name)

        parser.add_argument(
            "cluster_config_file",
            metavar="<cluster_config_file>",
            help=_("File describing the cluster configuration"))
        parser.add_argument(
            "--cluster-id",
            metavar="<cluster_id>",
            help=_("OpenShift cluster ID"))
        parser.add_argument(
            "--infra-env-id",
            metavar="<infra_env_id>",
            help=_("OpenShift infrastruction environment ID"))

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        cluster_id = parsed_args.cluster_id
        infra_env_id = parsed_args.infra_env_id

        with open(parsed_args.cluster_config_file) as f:
            cluster_config = json.load(f)

        missing_fields = list(
            set(self.REQUIRED_FIELDS).difference(cluster_config.keys()))
        if missing_fields:
            raise OrchestrationException(
                "Please specify these missing values in your config file: %s" %
                missing_fields)

        nodes = cluster_config.get('nodes')
        cluster_name = cluster_config.get('cluster_name')
        provisioning_network_name = cluster_config.get(
            'provisioning_network_name', 'provisioning')
        external_network_name = cluster_config.get('external_network_name')
        private_network_name = cluster_config.get('private_network_name')
        private_subnet_name = cluster_config.get('private_subnet_name')
        api_vip = cluster_config.get('api_vip')
        ingress_vip = cluster_config.get('ingress_vip')
        openshift_version = cluster_config.get('openshift_version')
        high_availability_mode = cluster_config.get(
            'high_availability_mode', 'Full')
        base_dns_domain = cluster_config.get('base_dns_domain')
        ssh_public_key = cluster_config.get('ssh_public_key')

        if 'PULL_SECRET' not in os.environ:
            raise OrchestrationException(
                'Please export PULL_SECRET in your environment')
        pull_secret = json.loads(os.environ['PULL_SECRET'])

        ironic_client = self.app.client_manager.baremetal
        neutron_client = self.app.client_manager.network

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + os.getenv('API_TOKEN', ''),
        }

        print("STARTING OPENSHIFT CLUSTER INSTALL")

        # get cluster id
        if not cluster_id:
            try:
                cluster_data = {
                    "name": cluster_name,
                    "openshift_version": openshift_version,
                    "high_availability_mode": high_availability_mode,
                    "base_dns_domain": base_dns_domain,
                    "api_vip": api_vip,
                    "ingress_vip": ingress_vip,
                    "ssh_public_key": ssh_public_key,
                    "pull_secret": pull_secret
                }
                response = call_assisted_installer_api(
                    'clusters', 'post', headers, cluster_data)
                cluster_id = response.json().get('id')
            except Exception as e:
                self._print_failure_message(
                    e,
                    parsed_args.cluster_config_file,
                    message='Error creating OpenShift cluster')
                raise OrchestrationException()
        print("cluster ID: %s" % cluster_id)

        # get infra env id
        if not infra_env_id:
            try:
                infra_env_data = {
                    "name": "%s-infra-env" % cluster_name,
                    "image_type": "minimal-iso",
                    "cluster_id": cluster_id,
                    "pull_secret": pull_secret,
                    "openshift_version": openshift_version,
                    "ssh_authorized_key": ssh_public_key
                }
                response = call_assisted_installer_api(
                    'infra-envs', 'post', headers, infra_env_data)
                infra_env_id = response.json().get('id')
            except Exception as e:
                self._print_failure_message(
                    e,
                    parsed_args.cluster_config_file,
                    cluster_id=cluster_id,
                    message='Error creating OpenShift cluster infra env')
                raise OrchestrationException()
        print("infra env ID: %s" % infra_env_id)

        # register nodes
        try:
            response = call_assisted_installer_api(
                "infra-envs/%s/hosts" % infra_env_id,
                'get', headers)
            host_count = len(response.json())
            if host_count < len(nodes):
                response = call_assisted_installer_api(
                    "infra-envs/%s/downloads/image-url" % infra_env_id,
                    'get', headers)
                image_url = response.json().get('url')
                provisioning_network = neutron_client.find_network(
                    provisioning_network_name)
                print("provisioning nodes")
                for node_name in nodes:
                    node = ironic_client.node.get(node_name)
                    if node.provision_state == 'available':
                        print("* deploying %s" % node_name)
                        port_name = utils.get_port_name(
                            provisioning_network.name, prefix=node_name)
                        port = utils.get_or_create_port(
                            port_name,
                            provisioning_network, neutron_client)
                        utils.boot_node_from_url(
                            node_name, image_url, port['id'],
                            ironic_client)
                    else:
                        print("* %s is in %s state" %
                              (node_name, node.provision_state))
                wait_for_nodes(
                    infra_env_id, headers, 3, 'pending-for-input')
            else:
                print('nodes already registered to cluster')
        except Exception as e:
            self._print_failure_message(
                e,
                parsed_args.cluster_config_file,
                cluster_id=cluster_id,
                infra_env_id=infra_env_id,
                message='Error registering nodes to OpenShift cluster')
            raise OrchestrationException()

        # move nodes to private network
        try:
            print("ensuring nodes are on private network %s" %
                  private_network_name)
            private_network = neutron_client.find_network(private_network_name)
            for node in nodes:
                already_attached = False
                bm_ports = ironic_client.port.list(node=node, detail=True)
                for bm_port in bm_ports:
                    port_uuid = bm_port.internal_info.get(
                        "tenant_vif_port_id", None)
                    if port_uuid:
                        port = neutron_client.find_port(port_uuid)
                        if port.network_id == private_network.id:
                            already_attached = True
                        else:
                            ironic_client.node.vif_detach(node, port_uuid)
                if already_attached:
                    print("* %s already on private network" % node)
                else:
                    print("* moving %s onto private network" % node)
                    port_name = utils.get_port_name(
                        private_network.name, prefix=node)
                    port = utils.get_or_create_port(
                        port_name, private_network, neutron_client)
                    ironic_client.node.vif_attach(node, port['id'])
                    ironic_client.node.set_boot_device(node, 'disk', True)
        except Exception as e:
            self._print_failure_message(
                e,
                parsed_args.cluster_config_file,
                cluster_id=cluster_id,
                infra_env_id=infra_env_id,
                message='Error preparing nodes after ' +
                'OpenShift cluster registration')
            raise OrchestrationException()

        # install cluster
        try:
            response = call_assisted_installer_api(
                "clusters/%s/" % cluster_id,
                'get', headers)
            cluster_status = response.json().get('status')
            if cluster_status != 'installed':
                if cluster_status not in ['installing',
                                          'preparing-for-installation']:
                    private_subnet = neutron_client.find_subnet(
                        private_subnet_name)
                    response = call_assisted_installer_api(
                        "clusters/%s" % cluster_id, 'patch', headers,
                        {'machine_network_cidr': private_subnet.cidr})
                    wait_for_nodes(
                        infra_env_id, headers, 3, 'known')
                    print("starting install...")
                    response = call_assisted_installer_api(
                        "clusters/%s/actions/install" % cluster_id,
                        'post', headers)
                waiting = True
                while waiting:
                    response = call_assisted_installer_api(
                        "clusters/%s/" % cluster_id,
                        'get', headers)
                    status = response.json().get('status')
                    if status == 'installing':
                        status = status + " " + str(
                            response.json().get('progress'))
                    print("* installation status: %s" % status)
                    if status == 'installed':
                        waiting = False
                    else:
                        time.sleep(30)
                print("... install complete")
            else:
                print("install already completed")
        except Exception as e:
            self._print_failure_message(
                e,
                parsed_args.cluster_config_file,
                cluster_id=cluster_id,
                infra_env_id=infra_env_id,
                message='Error installing OpenShift cluster')
            raise OrchestrationException()

        # assign floating IPs to apps and api endpoints
        try:
            print("checking for external floating IPs for "
                  "API and apps endpoints")
            external_network = neutron_client.find_network(
                external_network_name)
            private_network = neutron_client.find_network(private_network_name)
            private_subnet = neutron_client.find_subnet(private_subnet_name)

            api_port = utils.get_or_create_port_by_ip(
                api_vip, "%s-api" % cluster_name,
                private_network, private_subnet, neutron_client)
            api_fip = utils.get_or_assign_port_floating_ip(
                api_port, external_network, neutron_client)
            apps_port = utils.get_or_create_port_by_ip(
                ingress_vip, "%s-apps" % cluster_name,
                private_network, private_subnet, neutron_client)
            apps_fip = utils.get_or_assign_port_floating_ip(
                apps_port, external_network, neutron_client)
        except Exception as e:
            self._print_failure_message(
                e,
                parsed_args.cluster_config_file,
                cluster_id=cluster_id,
                infra_env_id=infra_env_id,
                message='Error during OpenShift cluster post-install')
            raise OrchestrationException()

        print("OPENSHIFT CLUSTER INSTALL COMPLETE")

        return ["Endpoint", "IP"], [
            ["API", api_fip.floating_ip_address],
            ["apps", apps_fip.floating_ip_address]]


class Undeploy(command.Command):
    """Undeploy an OpenShift cluster from ESI nodes"""

    log = logging.getLogger(__name__ + ".Undeploy")
    REQUIRED_FIELDS = ['nodes', 'private_network_name', 'api_vip',
                       'ingress_vip']

    def get_parser(self, prog_name):
        parser = super(Undeploy, self).get_parser(prog_name)

        parser.add_argument(
            "cluster_config_file",
            metavar="<cluster_config_file>",
            help=_("File describing the cluster configuration"))

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        with open(parsed_args.cluster_config_file) as f:
            cluster_config = json.load(f)

        missing_fields = list(
            set(self.REQUIRED_FIELDS).difference(cluster_config.keys()))
        if missing_fields:
            raise OrchestrationException(
                "Please specify these missing values in your config file: %s" %
                missing_fields)

        nodes = cluster_config.get('nodes')
        provisioning_network_name = cluster_config.get(
            'provisioning_network_name', 'provisioning')
        private_network_name = cluster_config.get('private_network_name')
        api_vip = cluster_config.get('api_vip')
        ingress_vip = cluster_config.get('ingress_vip')

        ironic_client = self.app.client_manager.baremetal
        neutron_client = self.app.client_manager.network

        print("STARTING UNDEPLOY")

        # delete apps and API floating and fixed IPs
        print("* removing API and ingress ports and fips")
        for ip in [api_vip, ingress_vip]:
            print("   * %s" % ip)
            ip_search_string = "ip_address=%s" % ip
            ports = list(neutron_client.ports(fixed_ips=ip_search_string))
            if len(ports) > 0:
                port = ports[0]
                fips = list(neutron_client.ips(fixed_ip_address=ip))
                if len(fips) > 0:
                    fip = fips[0]
                    print("   * %s" % fip.floating_ip_address)
                    neutron_client.delete_ip(fip.id)
                neutron_client.delete_port(port.id)

        # undeploy nodes
        print("* undeploying nodes")
        for node in nodes:
            print("   * %s" % node)
            ironic_client.node.set_provision_state(node, 'deleted')
        print("* waiting for nodes to start undeploy before deleting ports")
        time.sleep(15)

        # delete provisioning and private network ports
        print("* deleting Neutron ports")
        for node in nodes:
            provisioning_port_name = utils.get_port_name(
                provisioning_network_name, prefix=node)
            provisioning_port = neutron_client.find_port(
                provisioning_port_name)
            if provisioning_port:
                print("   * %s" % provisioning_port_name)
                neutron_client.delete_port(provisioning_port.id)
            private_port_name = utils.get_port_name(
                private_network_name, prefix=node)
            private_port = neutron_client.find_port(private_port_name)
            if private_port:
                print("   * %s" % private_port_name)
                neutron_client.delete_port(private_port.id)

        print("UNDEPLOY COMPLETE")
        print("-----------------")
        print("* node cleaning will take a while to complete")
        print("* run `openstack baremetal node list` to see if"
              " they are in the `available` state")
