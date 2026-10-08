# Test template: wellnest

Antithesis runs the test commands in this directory inside the workload
container (`/opt/antithesis/test/v1/wellnest/`). Each command's file name must
start with a recognized prefix: `parallel_driver_`, `singleton_driver_`,
`serial_driver_`, `first_`, `anytime_`, `eventually_`, or `finally_`.

Files starting with `helper_` (like this one) are ignored by Antithesis.

The commands are written in the workload step, from the property catalog in
`antithesis/scratchbook/property-catalog.md`.
