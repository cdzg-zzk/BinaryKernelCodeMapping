/* Diagnostic-only capture at the existing codec boundary; never used for timing. */
#define sq_codec_decode sq_codec_decode_original
#include "posix_io.c"
#undef sq_codec_decode
#include <stdio.h>
#include <string.h>
#include <limits.h>
static char capture_dir[PATH_MAX], capture_phase[128];
static unsigned capture_count;
void sq_diag_phase(const char *dir, const char *phase)
{
    snprintf(capture_dir,sizeof(capture_dir),"%s",dir);
    snprintf(capture_phase,sizeof(capture_phase),"%s",phase);
    capture_count=0;
}
int sq_codec_decode(void *handle,const void *input,size_t n,void *output,size_t capacity)
{
    int ret=sq_codec_decode_original(handle,input,n,output,capacity);
    if (((struct codec *)handle)->id==4 && ret>=0 && capture_dir[0] && capture_count<32) {
        char path[PATH_MAX+256]; FILE *f;
        snprintf(path,sizeof(path),"%s/%s-%03u.xz",capture_dir,capture_phase,capture_count);
        f=fopen(path,"wbx"); if(!f) abort();
        if(fwrite(input,1,n,f)!=n) abort(); fclose(f);
        snprintf(path,sizeof(path),"%s/%s-%03u.raw",capture_dir,capture_phase,capture_count);
        f=fopen(path,"wbx"); if(!f) abort();
        if(fwrite(output,1,(size_t)ret,f)!=(size_t)ret) abort(); fclose(f);
        capture_count++;
    }
    return ret;
}
