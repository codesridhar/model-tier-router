# Security policy

## Supported versions

Until `1.0`, security fixes are released for the latest minor version only. After `1.0`, this file
will list the supported release lines explicitly.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting feature for the repository. Do not open a public
issue for a suspected vulnerability. Include affected versions, reproduction steps, impact, and
any suggested mitigation. Maintainers should acknowledge a complete report within five business
days and coordinate disclosure after a fix is available.

## Security model

The core package makes no network calls, executes no user-provided code, and does not log query
text. Classifier adapters run with the host application's privileges. Applications are responsible
for authenticating callers, limiting request size, protecting prompt data sent to remote
classifiers, and treating `tier_override` as a trusted field.

Do not load pickled or joblib classifier artifacts from untrusted sources. Python model artifacts
may execute code during deserialization. This project deliberately does not provide automatic
classifier persistence.

