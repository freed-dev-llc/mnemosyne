# OPNsense: firewall model and intrusion detection

## How firewall rules are evaluated

OPNsense firewall rules are stateful by default: the first packet of an allowed flow creates a
state, and the return traffic matches that state instead of being re-checked against the rule set.
Rules live per interface and are evaluated first match, top to bottom, so the first rule that
matches decides the packet's fate and no later rule overrides it. By default an interface's rules
filter traffic in the inbound direction, as it enters the firewall from that network.

## Grouping rules with categories

As a rule set grows, OPNsense lets you tag each rule with one or more Categories and then filter
the rule list by category. Categories are a labeling and filtering aid in the GUI; they do not
change how rules are evaluated, but they make a large policy readable by grouping related rules
(for example all VPN rules or all guest rules) under a shared, colored label.

## Aliases

An alias is a named list, defined under Firewall > Aliases, that stands in for hosts, networks,
ports, or URLs inside rules, so you edit the list once instead of every rule that references it.
OPNsense supports nested aliases and GeoIP aliases that match traffic by country, which is handy
for coarse geographic blocking.

## Built-in intrusion detection

Unlike pfSense, which adds IDS/IPS through the Snort or Suricata add-on packages, OPNsense ships
Suricata built into the base system. You configure it in the web GUI under Services > Intrusion
Detection, choose the interfaces to inspect, select rule sources, and switch between detection
(IDS) and inline prevention (IPS) mode. Because it is part of the base, intrusion detection is
available without installing a plugin.
