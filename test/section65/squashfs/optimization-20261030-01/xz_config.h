/* Ordinary-user reference adaptation, separate from prepared kernel objects. */
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "sq_xz_api.h"
#define XZ_DEC_X86
#define XZ_DEC_POWERPC
#define XZ_DEC_IA64
#define XZ_DEC_ARM
#define XZ_DEC_ARMTHUMB
#define XZ_DEC_SPARC
#define GFP_KERNEL 0
#define kmalloc(n,g) malloc(n)
#define kfree(p) free(p)
#define vmalloc(n) malloc(n)
#define vfree(p) free(p)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define min(a,b) ((a)<(b)?(a):(b))
#define memeq(a,b,n) (memcmp(a,b,n)==0)
#define memzero(p,n) memset(p,0,n)
#define fallthrough __attribute__((fallthrough))
static inline uint32_t get_unaligned_le32(const void *p){uint32_t x;memcpy(&x,p,4);return x;}
static inline uint32_t get_unaligned_be32(const void *p){return __builtin_bswap32(get_unaligned_le32(p));}
static inline void put_unaligned_le32(uint32_t x,void *p){memcpy(p,&x,4);}
static inline void put_unaligned_be32(uint32_t x,void *p){x=__builtin_bswap32(x);memcpy(p,&x,4);}
#define get_le32(p) get_unaligned_le32(p)
