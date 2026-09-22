#ifndef VKSO_LZ4_OFFICIAL_BACKEND_ADAPTER_H
#define VKSO_LZ4_OFFICIAL_BACKEND_ADAPTER_H

int official_backend_open(const char *path, int kernel_api);
void official_backend_close(void);

#endif
