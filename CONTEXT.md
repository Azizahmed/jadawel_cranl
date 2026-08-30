# Jadawel Domain Language

Canonical language for concepts that are specific to Jadawel.

## MCP Data Protection

**MCP endpoint**:
A user-owned access point to one Jadawel workspace for clients that communicate
through the Model Context Protocol.
_Avoid_: MCP, MCP server instance

**Endpoint protection policy**:
The set of fields whose values one MCP endpoint must keep inside Jadawel's trust
boundary.
_Avoid_: Global sensitivity policy, workspace masking policy

**Policy revision**:
The version of an endpoint protection policy that changes whenever its protected
field membership or protection meaning changes.
_Avoid_: Field version, UI version

**Protected field**:
A Jadawel field selected in an endpoint protection policy; its cell values must
not cross that MCP endpoint in plaintext.
_Avoid_: Sensitive column, masked column

**Suspended protection entry**:
A policy entry retained for a temporarily unavailable field so restoring the same
field identity cannot silently expose its values.
_Avoid_: Deleted policy entry, inactive field

**Mask token**:
A time-limited opaque reference bound to a protected value and its cell's observed
row state; it can be returned only to its original protected cell to preserve that
value without revealing or copying it.
_Avoid_: Redacted value, display mask

**Mask-token redemption**:
The acceptance of a valid mask token in its original protected cell as an explicit
request to preserve the observed value.
_Avoid_: Demasking, secret recovery

**Token vault**:
A shared server-side collection that binds mask-token digests to their original
protected-cell context, observed row state, and expiry without storing plaintext.
_Avoid_: Token database, decryption service

**Stale mask token**:
A mask token whose protected value, observed row state, or protection context no
longer matches Jadawel's current state.
_Avoid_: Expired token, changed value

**Endpoint suspension**:
A reversible state in which an MCP endpoint cannot serve calls because its owner no
longer has the required workspace access, while its protection policy is retained.
_Avoid_: Endpoint deletion, temporary connection failure

**Endpoint access generation**:
The version of an MCP endpoint's owner-access context that changes when credentials,
membership, account state, or effective workspace permissions change.
_Avoid_: Policy revision, user role

**Protection-blocked endpoint**:
An MCP endpoint whose retained policy cannot currently be validated against the
available schema, so every call fails closed until the policy is made valid again.
_Avoid_: Suspended endpoint, unavailable field

**Protected derivative**:
A value whose disclosure would reproduce or expose information from a protected
field through a formula, lookup, linked-row label, search, or similar derivation.
_Avoid_: Safe computed value, indirect field

**Protection provenance**:
The set of protected source-field identities whose information is carried by a
returned value or one of its semantic parts.
_Avoid_: Mask flag, sensitive result

**Protected artifact draft**:
An MCP-authored candidate artifact that declares protected-field dependencies but
cannot receive or render their plaintext before approval.
_Avoid_: Pending page, masked HTML

**Artifact exposure manifest**:
The stable set of protected field identities and audience conditions an artifact
requests at render time.
_Avoid_: Token list, detected secrets

**Artifact exposure approval**:
A human authorization bound to one exact artifact revision, exposure manifest,
endpoint policy revision, and audience that permits protected values to be supplied
inside Jadawel at render time.
_Avoid_: Demasking permission, page approval

**Token issuance budget**:
The bounded number of mask tokens an MCP call, endpoint, or Jadawel deployment may
create during the tokens' lifetime window.
_Avoid_: Redis quota, request rate limit
