# pfSense: aliases and advanced rules

## Aliases

An alias is a named object that groups values you reference in firewall rules and NAT
instead of repeating raw addresses or ports. Aliases are managed under Firewall > Aliases,
and pfSense supports several alias types: a host alias holds one or more IP addresses, a
network alias holds CIDR networks, a port alias holds port numbers or ranges, and a URL
Table alias loads its list of networks from an external URL. Aliases can be nested — one
alias may contain another — and editing an alias updates every rule that references it,
which keeps a large rule set readable.

## URL Table aliases

A URL Table alias is how you feed a large or frequently-changing list into pfSense: it
downloads its addresses from a URL you specify and refreshes them on a schedule, so an
externally-maintained blocklist or allowlist stays current without hand-editing any rule.

## Floating rules

Floating rules live on the Floating tab under Firewall > Rules and are more flexible than
per-interface rules: a single floating rule can match on multiple interfaces at once and in
either direction, inbound or outbound. With the quick option set, a floating rule acts on
first match like an interface rule; without quick it uses last match, so a later matching
rule can still override it. Floating rules are evaluated before the per-interface rules,
which makes them the right place for network-wide policy such as traffic shaping.

## Rule separators

Rule separators are labeled, colored bars you insert between rules to group and annotate
them. A separator carries no action and never matches traffic; it exists only to keep a
long rule list organized and readable.
