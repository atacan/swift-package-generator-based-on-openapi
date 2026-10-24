# Migrating existing packages to four products

Upgrade existing packages in place. Keep your original specification, overlay,
custom Swift code, tests, and resources. There is no automatic scaffold migration;
`.swift-bootstrapper.yaml` still only needs its existing `package_name`.

1. **Run the latest generator from a clean commit or saved working tree.** For
   example, from this repository:

   ```bash
   uv run swift-bootstrapper bootstrap /path/to/SonioxAPI
   ```

   The command regenerates the sanitized specification, Swift sources, and operation
   security metadata. It adds missing helper files, transport directories, and test
   placeholders. Existing manifests, configuration, helpers, tests, README, and
   AGENTS.md are preserved. The manual manifest warning means the remaining steps
   are still required, even when code generation succeeds. Review generated model
   diffs too: updated schema transformations can change public property types.

2. **Merge the four-product manifest changes.** Use
   [Package.swift.j2](src/bootstrapper/resources/Package.swift.j2) as a reference;
   keep your existing custom dependencies, platform settings, and resource rules.
   Add `{Name}URLSession` and `{Name}AsyncHTTPClient` library products and targets.
   Add the `swift-openapi-urlsession` and `swift-http-types` package dependencies,
   retaining `swift-openapi-async-http-client` for its convenience target. Give
   Types and core direct `HTTPTypes` dependencies. Move the `OpenAPIAsyncHTTPClient`
   target dependency and transport imports out of core; each convenience target
   depends on core, `OpenAPIRuntime`, and its own transport product. Register the
   new test directories as test targets if you want to run them.

3. **Adopt shared authentication.** The new files live in
   `Sources/{Name}/Authentication/`. Update old
   `AuthenticationMiddleware(apiKey:)` call sites to the factories' `authentication:`
   parameter, or use the new middleware's `init(authentication:)` with a custom
   transport. Transfer any custom authentication behavior before removing the
   obsolete `Sources/{Name}Types/AuthenticationMiddleware.swift`. For a single
   bearer scheme, use `authentication: .bearer(apiKey)`; for header API keys or
   multiple schemes, follow the generated authentication helpers and the final
   overlaid specification. Moving/removing the old public middleware is a source
   compatibility change for downstream callers; document it when publishing.

4. **Preserve provider defaults and custom tests.** Factory helpers are editable
   and preserved on reruns. If your API returns fractional-second timestamps, set
   `configuration: Configuration = .init(dateTranscoder: .iso8601WithFractionalSeconds)`
   in both factories, keep explicit caller overrides working, and test response
   decoding through each factory. Keep dependencies such as `UsefulThings` and
   `.process("Resources")` when existing suites use them. Tests importing runtime,
   HTTP types, or a transport should declare those product dependencies directly.

5. **Verify and update your package documentation.** Run `swift build` and the
   offline test suites, then rerun the generator and check the diff to confirm
   your manual edits survive. Select offline suites explicitly if existing tests
   automatically use credentials from `.env`. Update the preserved README and
   AGENTS.md with the two factory examples and relevant troubleshooting guidance
   from the current templates. Run live tests separately when intended.

In the SonioxAPI trial, regeneration, `swift build`, and the seven existing
`ResponseDecodingTests` passed before migration. The preserved manifest still
exposed only two products and did not compile either new wrapper. Its old
`AuthenticationMiddleware(apiKey:)` calls also compiled; removing the legacy
middleware was an explicit API migration, not a fix for an observed compiler
ambiguity. The manifest changes and verification of both factories are therefore
necessary even when the first rerun reports success. Once wired into the manifest,
both factories failed to decode Soniox's `2026-10-03T14:40:37.263Z` fixture with
their generic date default (`Expected date string to be ISO8601-formatted`). Setting
the fractional-second default in both provider factories fixed that failure.
The migrated package's offline verification command is:

```bash
cd /path/to/SonioxAPI
swift build
swift test --filter 'ResponseDecodingTests|FactoryDefaultsTests|AuthenticationTests'
```

All 16 offline tests passed after the manual changes. A second generator run
preserved all 50 package files checked, including the manifest, custom tests,
factory defaults, documentation, and regenerated sources.

