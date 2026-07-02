# UniFi operations: adoption recovery, firmware, diagnostics

> **About this file:** a self-authored primer for this repo: original prose on UniFi networking
> practices. It is illustrative guidance, not official Ubiquiti documentation; verify specifics
> against current UniFi docs before acting.

## A device shows offline

When a device drops off the controller, work from the physical layer up: check the cable, confirm
PoE delivery, and look at the switch port. Then read the controller (Devices > [Device] > Last Seen
and status). If you still need to look inside, SSH to the device (`ssh root@<device-ip>` on UniFi
OS, `ssh ubnt@<device-ip>` on legacy), run `info`, and read `/var/log/messages`. Causes cluster
around connectivity loss, power, an IP conflict, a firmware crash, or an adoption problem.

## A device is stuck "Adopting"

A device that will not finish adopting usually cannot reach the controller's inform endpoint or is
still carrying a previous controller's credentials. The recovery sequence:

1. Forget the device in the controller.
2. Factory reset it (hold the reset button 10+ seconds, or over SSH `ubnt-systool reset2defaults`
   on UniFi OS, `set-default` on legacy).
3. Make sure the device can reach the controller on port 8080.
4. Point its inform URL at the controller: `ubnt-systool set-inform http://<controller-ip>:8080/inform`
   on UniFi OS, or `set-inform http://<controller-ip>:8080/inform` on legacy devices.
5. Re-adopt.

The error "Please adopt through the UniFi Network Application" is the same problem: the device's
inform URL does not match the controller, so reset the inform URL as above.

## Firmware upgrades and the UDM SE exception

UniFi devices take firmware three ways, and the right one depends on the device:

- **Controller UI** for APs, switches, and other non-gateway devices: Devices > [Device] > Settings
  > Manage > Firmware, or Upgrade All from the top bar.
- **Controller API** for programmatic upgrades of those same standard devices
  (`POST .../cmd/devmgr` with `{"mac": "...", "cmd": "upgrade"}`).
- **SSH** for UDM SE, UDM Pro, and UDR. These devices *are* the controller, so the API upgrade
  command cannot upgrade them. Use `ubnt-systool fwupdate <firmware-url>` for an online upgrade, or
  push a file with `scp firmware.bin root@<device-ip>:/tmp/fwupdate.bin` then
  `ubnt-systool fwupdate /tmp/fwupdate.bin` for an offline one.

The device reboots during an upgrade and the SSH session drops; that is expected. Always take a
controller backup first (Settings > System > Backup, or `POST .../cmd/backup`), check the current
version with `ubnt-device-info firmware`, and read the release notes. UniFi OS has no built-in
rollback, so keep the previous `.bin` file and the pre-upgrade backup if you may need to revert.

## Common network diagnostics

- **DHCP not working:** confirm the DHCP server is enabled for the network, the range still has free
  addresses, and there is not a second DHCP server fighting it. `cat /var/log/messages | grep dhcp`
  on the device helps.
- **Cannot reach another VLAN:** the usual cause is a firewall Drop rule; check Settings > Firewall
  & Security > Firewall Rules, then the routing and gateway config.
- **Can ping an IP but not a name:** a DNS problem. Check the network's DNS settings, try 8.8.8.8 or
  1.1.1.1, clear the client cache, and confirm DNS is not blocked by a firewall rule.

## Where the logs are

On the controller, application logs live in `/var/log/unifi/` (`server.log`, `mongod.log`). On a
device over SSH, the system log is `/var/log/messages`. From the UI, Settings > System > Support
Info downloads a support bundle for deeper analysis.
