# Runtime resources

Copy a compatible `LibreHardwareMonitorLib.dll` into this directory before running or building:

```text
resources/LibreHardwareMonitorLib.dll
```

The DLL is intentionally not committed to this repository. Obtain it from the official LibreHardwareMonitor project/release and verify its license and redistribution terms before publishing a binary release.

The application accepts an explicit DLL path through the `FI4_LHM_DLL` environment variable. This is useful during development when the DLL is stored outside the repository.
