#    Copyright (c) 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json

from tempest.lib.common.utils import data_utils


def kwargs_to_flags(valid_flags, arguments):
    """kwargs to flag helper

    Takes an iterable containing a list of valid flags and a flattened
    kwargs dict containing the flag values received by the function.

    The key for each dict entry should be the name of a valid flag for the
    command being run, with any hyphens in the flag name replaced with
    underscores (e.g. end-time -> end_time). Its corresponding value
    should be a string, True (if that flag is included by itself),
    or None/False to indicate the flag should be excluded.

    Returns a stringified version of kwargs for use with CLI commands.

    """
    flag_string = ''
    for flag in arguments.keys():
        val = arguments[flag]
        if val is not None:
            if flag in valid_flags:
                tmp = ' --%s' % flag.replace('_', '-')
                if type(val) == str:
                    flag_string += '%s "%s"' % (tmp, val)
                elif type(val) == bool:
                    flag_string += tmp if val else ''
                else:
                    raise TypeError('Invalid value for flag %s, expected \
                                     type \'str\' or \'bool\' and got type \
                                     \'%s\'' % (flag, type(val).__name__))
            else:
                raise NameError('Invalid flag with name %s' % flag)
    return flag_string


def node_create(client, driver='fake-hardware', name=None, fail_ok=False,
                **kwargs):

    if not name:
        name = data_utils.rand_name('baremetal-node')

    kwargs['name'] = name
    kwargs['driver'] = driver

    valid_flags = ('driver', 'name', )

    flags = kwargs_to_flags(valid_flags, kwargs)
    flags += ' -f json'

    output = client.baremetal('node create', flags, '', fail_ok)
    return json.loads(output)


def node_delete(client, identifier, fail_ok=False):
    return client.baremetal('node delete', '', identifier, fail_ok)


def node_power_on(client, identifier, fail_ok=False):
    return client.baremetal('node power on', '', identifier, fail_ok)


def node_power_off(client, identifier, fail_ok=False):
    return client.baremetal('node power off', '', identifier, fail_ok)


def node_set(client, identifier, fail_ok=False, **kwargs):

    valid_flags = ('owner', 'lessee', )

    flags = kwargs_to_flags(valid_flags, kwargs)

    return client.baremetal('node set', flags, identifier, fail_ok)
