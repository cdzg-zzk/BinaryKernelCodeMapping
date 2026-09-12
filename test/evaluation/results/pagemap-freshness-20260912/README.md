# Buffered pagemap observation

An ordinary UID 1000 process mapped two adjacent anonymous pages. It faulted
the first page and read its pagemap entry through Python's default buffered
file object, then faulted the second page. Seeking to the second entry in the
same buffered object still returned a non-present entry; `os.pread()` on the
same descriptor returned the now-present entry. Only presence bits were
examined; PFN fields remain hidden for this ordinary process.

[`observation.json`](observation.json) records the four entries and assertions.
This reproduces the stale-buffer mechanism encountered by the LZ4 guest
observer on adjacent mappings. It is an observation-tool check, not a kernel
mapping failure or a performance measurement. The frozen Clocktime helper
was not changed; the new LZ4 observer uses fresh reads after each page fault.
