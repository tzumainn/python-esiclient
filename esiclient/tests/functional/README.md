# esi Client Functional Tests

These tests are designed to ensure Ironic and Neutron behave as expected when configured with the Ironic policy file given here: [https://github.com/CCI-MOC/esi/blob/master/etc/ironic/policy.yaml.sample]. Alternatively, an Ironic config file path can passed via the evironment variable `OS_IRONIC_CFG_PATH`.

### Prerequisites

These tests are intended to be ran against a functioning OpenStack cloud with Ironic and Neutron services enabled and running. It assumes that the ironic.conf file
is located at `/etc/ironic/ironic.conf`. These tests assume that the `fake-hardware` hardware type is enabled under the `enabled_hardware_types` option under `[DEFAULT]` heading. Some of these tests require an Ironic node configured with ipmi credentials in order to test the use of the ipmitool-socat serial console.
Details for configuring the serial console can be found here: [https://docs.openstack.org/ironic/latest/admin/console.html]
Some tests require further configuration. This can be provided by doing the following:

```
$ cd esiclient/tests/functional/
$ cp test.conf.sample test.conf
$ # edit test.conf with appropriate values
```

### Running the tests

By default, the functional tests will not run when invoking `tox` with no additional options. To run them, you must specify the 'functional' testenv like this:

```
$ tox -e functional
```

You can also run a subset of the tests:

```
# run only the image tests:
$ tox -e functional -- -k "ImageTests"
# run everything except the image tests:
$ tox -e functional -- -k "not ImageTests"
# run a single specific test:
$ tox -e functional -- -k "test_admin_image_public_and_private"
```
