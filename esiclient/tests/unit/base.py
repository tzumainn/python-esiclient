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
import testtools


class TestCase(testtools.TestCase):
    """Base class for all unit tests"""

    def setUp(self):
        super(TestCase, self).setUp()


class TestCommand(TestCase):
    """Base class for all command unit tests"""

    def setUp(self):
        super(TestCommand, self).setUp()
        self.app = mock.Mock()
        self.app.client_manager = mock.Mock()
        self.app.client_manager.baremetal = mock.Mock()
        self.app.client_manager.network = mock.Mock()

    def check_parser(self, cmd, args, verify_args):
        cmd_parser = cmd.get_parser("check_parser")
        parsed_args = cmd_parser.parse_args(args)
        for av in verify_args:
            attr, value = av
            if attr:
                self.assertIn(attr, parsed_args)
                self.assertEqual(getattr(parsed_args, attr), value)
        return parsed_args
