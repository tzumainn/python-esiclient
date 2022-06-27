# python-esiclient

`python-esiclient` extends the OpenStack CLI to provide simplified user workflows, encapsulating multiple OpenStack CLI commands into a single CLI command.

To install this package using PyPI,
 - `pip install python-esiclient`

## `openstack esi node network <command>`

These commands manage network connections to nodes.

### `openstack esi node network list`

List node/network attachments.

```
openstack esi node network list
   [--node <node>]
   [--network <network>]
```

- `--node <node>`: Filter by node (name or UUID)
- `--network <network>`:  Filter by network (name or UUID)

### `openstack esi node network attach`

Attach network to a node.

```
openstack esi node network attach
   (--network <network> | --port <port>)
   [--mac-address <mac-address>]
   <node>
```

- `--network <network>`:  Network (name or UUID)
- `--port <port>`:  Neutron port (name or UUID)
- `--mac-address <mac-address>`:  Node MAC address to attach the network to.
- `node`: Node (name or UUID)

### `openstack esi node network detach`

Detach network from a node.

```
openstack esi node network detach
   <node>
   <port>
```

- `node`: Node (name or UUID)
- `port`: Port (name or UUID)

## `openstack esi trunk <command>`

These commands manage trunk ports.

### `openstack esi trunk list`

List trunk ports.

```
openstack esi trunk list
```

### `openstack esi trunk create`

Create a trunk port.

```
openstack esi trunk create
   [--native-network <native-network>]
   [--tagged-networks <tagged-network>]
   <name>
```

- `--native-network <native-network>`: Native network (name or UUID)
- `--tagged-networks <tagged-network>`:  Tagged network (name or UUID); can specify multiple
- `name`: Name of the trunk port

### `openstack esi trunk add network`

Add a network to a trunk port.

```
openstack esi trunk add network
   [--tagged-networks <tagged-network>]
   <name>
```

- `--tagged-networks <tagged-network>`:  Tagged network (name or UUID); can specify multiple
- `name`: Name of the trunk port

### `openstack esi trunk remove network`

Remove a network from a trunk port.

```
openstack esi trunk remove network
   [--tagged-networks <tagged-network>]
   <name>
```

- `--tagged-networks <tagged-network>`:  Tagged network (name or UUID); can specify multiple
- `name`: Name of the trunk port

### `openstack esi trunk delete`

Delete a trunk port.

```
openstack esi trunk delete
   <name>
```

- `name`: Name of the trunk port

### `openstack esi node volume attach`

Boot a node with a volume

```
openstack esi node volume attach
   (--network <network> | --port <port>)
   [--mac-address <mac-address>]
   <node> <volume>
```

- `--network <network>`:  Network (name or UUID)
- `--port <port>`:  Neutron port (name or UUID)
- `node`: Node (name or UUID)
- `volume`: Volume (name or UUID)
