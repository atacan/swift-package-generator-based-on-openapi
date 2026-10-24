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

   If generation fails parsing an integer constraint, inspect the original spec
   and overlay for scientific notation in integer-only fields. Some parsers reject
   these spellings even when the value is a whole number. For example, normalize
   `maxLength: 2.083e+3` to `maxLength: 2083`, `minLength: 1e+0` to `minLength: 1`,
   and an integer schema's `default: 0e+0` to `default: 0`. Preserve the exact value;
   only normalize mathematically integral values. Make the correction in the
   original spec or overlay and rerun the bootstrapper so it survives regeneration.

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

   Preserve custom products and targets such as realtime/WebSocket types, along
   with their source directories, generator configurations, resources, and tests.
   The four-product structure describes the HTTP client; a package with a separate
   realtime product can expose five products. Keep custom generation commands such
   as `make generate-realtime` and include them in the regeneration step before
   the final build and tests.

   Move custom helpers such as `createClient(apiKey:)` that construct a specific
   transport into `Sources/{Name}AsyncHTTPClient/` or `Sources/{Name}URLSession/`.
   Preserve their server URL, timeout, runtime configuration, and middleware
   behavior. Update callers and tests to depend on and import the helper's new
   transport product; document this module change for downstream users.

   Carry over the helper's imports and declare their package/product dependencies
   directly in the receiving target. For example, a public AsyncHTTPClient factory
   default using `.init(timeout: .minutes(10))` needs `import NIOCore` in its Swift
   file, a direct `swift-nio` package dependency in `Package.swift`, and
   `.product(name: "NIOCore", package: "swift-nio")` in the AsyncHTTPClient target's
   dependencies. Retain `import OpenAPIAsyncHTTPClient` and its product dependency
   there too. Missing imports for public default arguments can produce a warning
   that becomes an error in Swift 6 language mode; do not rely on transitive imports.
   Keep explicit caller overrides working when carrying defaults into factories.

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

   When the specification declares multiple bearer schemes, `.bearer(...)` cannot
   choose between them. Use named credentials matching the exact scheme names in
   the final overlaid specification. For example, a package with separate regular
   and administration schemes can use:

   ```swift
   let authentication = Authentication.credentials([
       "ApiKeyAuth": .init(apiKey),
       "AdminApiKeyAuth": .init(adminApiKey),
   ])
   ```

   Pass this value to either factory's `authentication:` parameter. Supply only
   the credentials needed for the operations you call; shared authentication
   selects credentials according to each operation's security requirements.
   Verify regular and administration operations with offline authentication tests.

4. **Preserve provider defaults and custom tests.** Factory helpers are editable
   and preserved on reruns. If your API returns fractional-second timestamps, set
   `configuration: Configuration = .init(dateTranscoder: .iso8601WithFractionalSeconds)`
   in both factories, keep explicit caller overrides working, and test response
   decoding through each factory. Keep dependencies such as `UsefulThings` and
   `.process("Resources")` when existing suites use them. Tests importing runtime,
   HTTP types, or a transport should declare those product dependencies directly.

5. **Regenerate before the final build and tests.** After merging manifest changes,
   resolve dependencies with `swift package resolve`.

   Check `swift --version` against the resolved dependencies' `// swift-tools-version:`
   headers in `.build/checkouts/*/Package.swift` and their documented compiler
   requirements. Your root manifest's tools-version header does not guarantee that
   newer dependencies support that Swift version. In the ElevenLabs trial, the
   preserved older header coexisted with dependencies requiring Swift 6.2+.
   Use a compatible toolchain or adjust dependency constraints to retain your
   intended Swift support, and update the package README's minimum requirements.

   Check the preserved Makefile before using `make regenerate`. If that target is
   missing, merge an inline recipe such as this into the existing file:

   ```make
   .PHONY: regenerate
   regenerate: ; uvx --from git+https://github.com/atacan/swift-package-generator-based-on-openapi.git swift-bootstrapper bootstrap .
   ```

   Preserve custom recipes and include additional generation steps, such as
   `$(MAKE) generate-realtime`, when required by the package. Use literal tabs for
   commands added on separate recipe lines. Existing recipes
   using `swift-bootstrapper .` remain supported; changing them to the explicit
   `bootstrap` form is optional. Makefiles are preserved on reruns, so template
   updates do not add missing targets automatically.

   Then rerun the bootstrapper and any custom generation steps.
   Updated dependency requirements can select a newer `swift-openapi-generator`
   and change generated source contents or file layout. In the AzureSpeech trial,
   the generator changed from 1.12.2 to 1.14.2 and split Types into additional files.
   Review the diff and confirm your manual edits survived, then run `swift build`
   and the offline test suites against the regenerated output. If you regenerate
   again and the output changes, repeat the final build and tests. Select offline
   suites explicitly if existing tests automatically use credentials from `.env`.
   Update the preserved README and AGENTS.md with the two factory examples and
   relevant troubleshooting guidance from the current templates. Run live tests
   separately when intended.

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
# From the bootstrapper repository, after editing the target manifest:
swift package --package-path /path/to/SonioxAPI resolve
uv run swift-bootstrapper bootstrap /path/to/SonioxAPI
cd /path/to/SonioxAPI
swift build
swift test --filter 'ResponseDecodingTests|FactoryDefaultsTests|AuthenticationTests'
```

All 16 offline tests passed after the manual changes. A second generator run
preserved all 50 package files checked, including the manifest, custom tests,
factory defaults, documentation, and regenerated sources.

