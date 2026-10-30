// SPDX-License-Identifier: GPL-2.0-only
/* Apptainer helper argument translation; no filesystem parsing. */
#define _GNU_SOURCE
#include <errno.h>
#include <getopt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void json_string(FILE *stream, const char *value)
{
    fputc('"',stream);
    for (const unsigned char *p=(const unsigned char *)value; *p; p++) {
        if (*p=='"' || *p=='\\') fprintf(stream,"\\%c",*p);
        else if (*p<32) fprintf(stream,"\\u%04x",*p);
        else fputc(*p,stream);
    }
    fputc('"',stream);
}
int main(int argc, char **argv)
{
    const char *frontend=NULL,*core="-",*bridge="-",*trace=NULL,*kind="reader",*memory="16";
    static const struct option config[]={
        {"frontend",1,NULL,'F'},{"core",1,NULL,'C'},{"bridge",1,NULL,'B'},
        {"trace",1,NULL,'T'},{"kind",1,NULL,'K'},{"memory",1,NULL,'M'},{0,0,0,0}};
    int option;
    while ((option=getopt_long(argc,argv,"+",config,NULL))!=-1) {
        switch (option) {
        case 'F':frontend=optarg;break; case 'C':core=optarg;break;
        case 'B':bridge=optarg;break; case 'T':trace=optarg;break;
        case 'K':kind=optarg;break; case 'M':memory=optarg;break;
        default:return 2;
        }
    }
    if (!frontend || !trace) return 2;
    int first=optind;
    if (first==argc) {
        puts("usage: squashfuse_ll -f [-o uid=N,gid=N,offset=N,ro,allow_other] IMAGE MOUNT");
        return 0;
    }
    size_t capacity=128+strlen(memory);
    for (int i=first;i<argc;i++) capacity+=strlen(argv[i])+1;
    char *options=calloc(1,capacity),*source=NULL,*target=NULL;
    if (!options) return 1;
    unsigned long long offset=0;
    int foreground=0;
    for (int i=first;i<argc;i++) {
        if (!strcmp(argv[i],"-f")) { foreground=1;continue; }
        if (!strcmp(argv[i],"-o") && ++i<argc) {
            char *copy=strdup(argv[i]),*save=NULL;
            if (!copy) return 1;
            for (char *token=strtok_r(copy,",",&save); token; token=strtok_r(NULL,",",&save)) {
                if (!strncmp(token,"offset=",7)) {
                    char *end; errno=0;
                    offset=strtoull(token+7,&end,10);
                    if (errno || end==token+7 || *end || token[7]=='-') return 2;
                } else {
                    if (*options) strcat(options,",");
                    strcat(options,token);
                }
            }
            free(copy);continue;
        }
        if (i>=argc || argv[i][0]=='-') return 2;
        if (!source) source=argv[i]; else if (!target) target=argv[i]; else return 2;
    }
    if (!foreground || !source || !target) return 2;
    char offset_text[32];snprintf(offset_text,sizeof(offset_text),"%llu",offset);
    char **command=calloc(argc+12,sizeof(*command));
    if (!command) return 1;
    int n=0;command[n++]=(char *)frontend;
    if (!strcmp(kind,"reader")) {
        command[n++]=(char *)core;command[n++]=(char *)bridge;
        command[n++]=source;command[n++]=offset_text;command[n++]=target;
        if (*options) command[n++]=options;
    } else if (!strcmp(kind,"stock")) {
        for (int i=first;i<argc;i++) command[n++]=argv[i];
    } else if (!strcmp(kind,"lkl")) {
        size_t used=strlen(options);
        snprintf(options+used,capacity-used,"%stype=squashfs,mb=%s,offset=%llu",used ? "," : "",memory,offset);
        command[n++]=source;command[n++]=target;command[n++]="-f";command[n++]="-s";
        command[n++]="-o";command[n++]=options;
    } else return 2;
    FILE *log=fopen(trace,"a");
    if (!log) { perror(trace);return 1; }
    fprintf(log,"{\"pid\":%ld,\"source\":",(long)getpid());json_string(log,source);
    fputs(",\"target\":",log);json_string(log,target);
    fprintf(log,",\"offset\":%llu,\"options\":",offset);json_string(log,options);
    fputs(",\"command\":[",log);
    for (int i=0;i<n;i++) { if (i) fputc(',',log);json_string(log,command[i]); }
    fputs("]}\n",log);
    if (fclose(log)) return 1;
    execv(frontend,command);perror(frontend);return 1;
}
