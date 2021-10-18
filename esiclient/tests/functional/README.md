# esi Client Functional Tests

These tests are designed to ensure Ironic and Neutron behave as expected when configured with the Ironic policy file given here: [a link](https://github.com/CCI-MOC/esi/blob/master/etc/ironic/policy.yaml.sample). Alternatively, an Ironic config file path can passed via the evironment variable `OS_IRONIC_CFG_PATH`.

### Prerequisites

These tests are intended to be ran against a functioning OpenStack cloud with Ironic and Neutron services enables and running. It assumes that the ironic.conf file
is located at `/etc/ironic/ironic.conf`. These tests assume that the `fake-hardware` hardware type is enabled under the `enabled_hardware_types` option under `[DEFAULT]` heading.

### Running the tests

By default, the functional tests will not run when invoking `tox` with no additional options. To run them, you must specify the 'functional' testenv like this:

```
$ tox -e functional
```
