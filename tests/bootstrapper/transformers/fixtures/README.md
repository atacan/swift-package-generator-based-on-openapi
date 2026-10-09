# OpenAI discriminator regression fixture

`openai_discriminator_mappings.yaml` was extracted from the sibling
`swift-openai-api` repository's `original_openapi.yaml` and `openapi-overlay.yaml`.
The fixture records SHA-256 hashes of both source files, so its provenance can be
verified without depending on the sibling checkout when tests run.

The 12 standalone discriminator mapping updates are copied exactly from the overlay,
covering 174 entries. The schema fixture retains their source unions, plus the
unsafe `Item`, `InputItem`, and `RealtimeTurnDetection` examples and all transitive
local references needed to inspect their discriminator constraints. Union branch
order, discriminator property names, full required arrays, `allOf`, `$ref`, schema
types, and discriminator `type`/`role` const or enum values are copied unchanged.
Payload properties and annotations unrelated to those proofs are omitted, reducing
the fixture to 207 component schemas. Its test inputs retain source `const` values;
both direct inference and the complete const-normalizing pipeline are tested.

The overlay's `TranscriptTextDoneEvent.usage` change adds a branch and is deliberately
excluded from the expected mappings: mapping inference cannot invent API variants.
Its unmodified event schema remains in the fixture as a referenced source branch.
