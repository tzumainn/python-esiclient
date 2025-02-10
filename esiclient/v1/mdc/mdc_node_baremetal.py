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

import openstack
from osc_lib.command import command
from osc_lib.i18n import _


class MDCBaremetalNodeList(command.Lister):
    """List baremetal nodes from multiple OpenStack instances"""

    log = logging.getLogger(__name__ + ".List")
    auth_required = False

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("--ignore-invalid", "-i", action="store_true")
        parser.add_argument(
            "clouds",
            metavar="<clouds>",
            nargs="*",
            help=_("Specify the cloud to use from clouds.yaml."),
            default=openstack.config.OpenStackConfig().get_cloud_names(),
        )

        return parser

    def take_action(self, parsed_args):
        columns = [
            "Cloud",
            "UUID",
            "Name",
            "Instance UUID",
            "Power State",
            "Provisioning State",
            "Maintenance",
        ]
        data = []

        for cloud in parsed_args.clouds:
            try:
                data.extend(
                    [
                        cloud,
                        node.id,
                        node.name,
                        node.instance_id,
                        node.power_state,
                        node.provision_state,
                        node.is_maintenance,
                    ]
                    for node in openstack.connect(cloud=cloud).list_machines()
                )
            except Exception as err:
                if parsed_args.ignore_invalid:
                    self.log.error(
                        "failed to retrieve information for cloud %s: %s", cloud, err
                    )
                    continue
                raise

        return columns, data
