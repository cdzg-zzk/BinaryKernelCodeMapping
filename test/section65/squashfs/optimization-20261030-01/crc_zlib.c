/* Match the prepared user service: standard XZ CRC32 via the same libz. */
#include <stdint.h>
#include <stddef.h>
#include <zlib.h>
void xz_crc32_init(void) { }
uint32_t xz_crc32(const uint8_t *p,size_t n,uint32_t crc)
{ return (uint32_t)crc32_z(crc,p,n); }
