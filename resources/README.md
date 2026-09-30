# Runtime resources

Run the source build script to compile LibreHardwareMonitor and populate this directory:

~~~powershell
..\scripts\build_lhm.ps1
~~~

It builds official tag v0.9.6 for .NET 8 and copies LibreHardwareMonitorLib.dll, its runtime assemblies, and upstream license notices here. The binaries are local build outputs and are excluded from Git. Rebuild them after cloning the repository.

The application accepts an explicit DLL path through the FI4_LHM_DLL environment variable for development.
