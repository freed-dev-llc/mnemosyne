# UniFi networking — seed concepts

> **About this file:** a short, self-authored primer written *for this repo* so that
> `mnemosyne ingest ubiquiti` works out of the box with no network access. It is
> illustrative, not official Ubiquiti documentation — replace or augment it with real
> docs you have the right to use (see `sources.yaml`). Treat specifics as general guidance
> and verify against current UniFi documentation before acting on them.

## The UniFi model: controller, devices, sites

A UniFi network is organized around a **controller** (the UniFi Network application) that
manages **devices** (switches, access points, gateways) grouped into a **site**. The
controller holds the configuration; devices are stateless-ish executors that pull their
config from it. The controller can run on a UniFi **Cloud Gateway** or **Dream Machine**,
on a self-hosted host, or be reached via remote management. Understanding this split —
*the controller decides, the device enforces* — explains most of UniFi's behavior.

## Adoption: bringing a device under management

**Adoption** is the handshake that puts a factory-default or migrated device under a
controller's management. A device must be able to *reach* the controller (Layer 3
reachability and the correct inform URL) before it can be adopted. The typical lifecycle a
device reports is: **Pending Adoption → Adopting → Provisioning → Connected**. If a device
oscillates between states (an "adoption loop", most often cleared by a factory reset or a
corrected inform URL), the usual causes are:

- The device cannot resolve or reach the controller's **inform** address.
- A previous controller's credentials are still on the device (it needs a factory reset, or
  SSH `set-inform` pointed at the right URL).
- Firmware mismatch between device and controller, requiring an upgrade during provisioning.

For a device on a **different network** from the controller (remote adoption), the
controller's inform URL must be reachable from the device — commonly via Layer 3 routing, a
VPN/overlay, or setting the inform URL manually over SSH (`set-inform http://<host>:8080/inform`).

## Switching essentials

UniFi switches forward at Layer 2 by default and are configured centrally from the
controller. The concepts that come up most:

- **VLANs / Networks.** You define networks (each with a VLAN ID) in the controller, then
  assign them to switch ports via **port profiles**. A port profile bundles the native
  (untagged) network and the set of tagged networks allowed on that port.
- **Trunk vs access.** A port carrying one untagged network is effectively an *access*
  port; a port carrying tagged VLANs (e.g. the "All" profile) is a *trunk* to another
  switch or AP.
- **PoE.** Many UniFi switches supply Power over Ethernet; per-port PoE mode (auto/off, and
  PoE cycling) is set in the port's configuration — power-cycling a stuck AP is often done
  by toggling PoE on its port.

## Wireless essentials

Access points broadcast **WLANs** (SSIDs) defined centrally. Each WLAN maps to a network
(and thus a VLAN), so "guest" vs "IoT" vs "main" separation is usually expressed as
distinct WLANs bound to distinct VLAN-backed networks. RF behavior — channel, width, and
transmit power — can be auto-optimized or pinned per radio.

## Where Argus fits

[Argus](https://github.com/freed-dev-llc/argus) *discovers* a UniFi site through its UniFi
vendor pack — enumerating devices, clients, and uplink topology and reconciling that truth
into NetBox. Mnemosyne is the complementary *explainer*: when discovery surfaces something
(a switch in an odd state, an unexpected VLAN), Mnemosyne answers "what does this mean and
what should I do about it?" — grounded in the documentation you've ingested here.
