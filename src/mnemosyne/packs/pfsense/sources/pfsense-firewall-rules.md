# pfSense: firewall rules

## How rules are organized

Firewall rules in pfSense live on per-interface tabs (WAN, LAN, and any OPT interfaces) plus a
Floating tab. Each interface keeps its own ordered list of rules, managed under Firewall > Rules.

## Evaluation order

pfSense evaluates the rules on each interface from the top down, and the first match wins: as
soon as a packet matches a rule, that rule's action is applied and evaluation stops. Because of
this, more specific rules belong above broader ones. Interface rules are applied in the inbound
direction on that interface, filtering traffic as it enters the firewall from that network.

## Stateful filtering

pfSense rules are stateful by default. When traffic matches a pass rule, pfSense creates a
state table entry for that connection, and reply traffic is permitted automatically by that
state without a matching rule in the other direction. A rule's action is pass (allow), block
(drop silently), or reject (drop and notify the sender).

## Aliases

An alias is a named group of hosts, networks, or ports that you reference in rules instead of
repeating raw values. A WebPorts alias holding 80 and 443, for example, lets one rule cover both,
and editing the alias updates every rule that uses it.

## Floating rules

Floating rules sit on the Floating tab and can match on multiple interfaces and in either
direction at once. With quick set, a floating rule acts first-match like an interface rule;
without quick it acts last-match, so a later matching rule can override it. Floating rules suit
policies that must apply network-wide, such as traffic shaping.
