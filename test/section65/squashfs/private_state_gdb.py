"""Run inside GDB on a paused, untimed helper; read objects without inferior calls."""
import json
import functools
import os
from pathlib import Path
import gdb


@functools.lru_cache(maxsize=None)
def size(name):
    return int(gdb.parse_and_eval('sizeof('+name+')'))


image=gdb.parse_and_eval('(struct sq_image *)image_handle')
print('private snapshot: image located',flush=True)
assert 0<int(image)<(1<<47)
im=image.dereference()
filesystem=im['sb']['s_fs_info'].cast(gdb.lookup_type('struct squashfs_sb_info').pointer())
assert 0<int(filesystem)<(1<<47)
sb=filesystem.dereference()
count=0;seen=set();node=im['inodes']
while int(node):
    address=int(node);assert address not in seen and address<(1<<47);seen.add(address)
    count+=1;node=node.dereference()['next']
print('private snapshot: inode count',count,flush=True)
names=0;name_bytes=0;seen=set()
for bucket in range(1024):
    node=im['names'][bucket]
    while int(node):
        address=int(node);assert address not in seen and address<(1<<47);seen.add(address)
        item=node.dereference();names+=1
        name_bytes+=size('struct cached_name')+int(item['length'])
        node=item['next']
print('private snapshot: name count',names,flush=True)
caches=[]
for field in ['block_cache','fragment_cache','read_page']:
    pointer=sb[field]
    if not int(pointer):continue
    assert 0<int(pointer)<(1<<47)
    c=pointer.dereference();entries=int(c['entries']);pages=int(c['pages'])
    buffers=[int(c['entry'][i]['data'][0]) for i in range(entries)]
    assert all(0<v<(1<<47) for v in buffers)
    caches.append(dict(kind=field,entries=entries,pages_per_entry=pages,
        cache_address=hex(int(pointer)),buffer_addresses=[hex(v) for v in buffers],
        block_size=int(c['block_size']),buffer_bytes=entries*pages*4096,
        requested_bytes=size('struct squashfs_cache')+entries*(size('struct squashfs_cache_entry')+
            size('struct squashfs_page_actor')+pages*size('void *')+pages*4096)))
stream_pointer=sb['stream'].cast(gdb.lookup_type('struct user_stream').pointer())
assert 0<int(stream_pointer)<(1<<47)
stream=stream_pointer.dereference()
parts=dict(image_object=size('struct sq_image'),filesystem_object=size('struct squashfs_sb_info'),
    inode_objects=count*size('struct cached_inode'),name_objects=name_bytes,
    caches=sum(c['requested_bytes'] for c in caches),
    stream_object=size('struct user_stream'),stream_output=int(stream['capacity']))
result=dict(status='pass',image_address=hex(int(image)),inode_count=count,name_count=names,
    filesystem_address=hex(int(filesystem)),stream_address=hex(int(stream_pointer)),
    caches=caches,requested_bytes_by_category=parts,accounted_requested_bytes=sum(parts.values()),
    scope='Live user-owned allocations read through DWARF; subset, not RSS or full allocator usage.',
    excluded=['allocator metadata and rounding','codec-library internal allocations',
              'filesystem index tables and meta-index','FUSE and dynamic-loader allocations',
              'transient I/O buffers absent at this idle snapshot'])
Path(os.environ['VKSO_SNAPSHOT_OUTPUT']).write_text(json.dumps(result,indent=2)+'\n')
