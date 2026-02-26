OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)

PHDRS {
  text    PT_LOAD    FLAGS(0x5);   /* PF_R | PF_X */
  data    PT_LOAD    FLAGS(0x6);   /* PF_R | PF_W */
  dynamic PT_DYNAMIC FLAGS(0x6);
}

SECTIONS {
  . = 0x1000;

  . = ALIGN(0x1000);
  .text :
  {
    *(.text.clone_xxh32)
    *(.text .text.*)
    *(.plt .plt.*)
    *(.plt.got)
    *(.plt.sec)
  } :text

  .dynamic ALIGN(0x1000) : { *(.dynamic) } :data :dynamic
  .dynsym  ALIGN(0x1000) : { *(.dynsym)  } :data
  .dynstr  ALIGN(0x1000) : { *(.dynstr)  } :data
  .gnu.hash ALIGN(0x1000): { *(.gnu.hash) } :data
  .hash ALIGN(0x1000)    : { *(.hash)    } :data
  .rela.dyn ALIGN(0x1000): { *(.rela.dyn) } :data
  .rela.plt ALIGN(0x1000): { *(.rela.plt) } :data
  .got ALIGN(0x1000)     : { *(.got .got.* .got.plt) } :data
  .data ALIGN(0x1000)    : { *(.data .data.*) } :data
  .bss  ALIGN(0x1000)    : { *(.bss .bss.* COMMON) } :data

  /DISCARD/ : {
    *(.init)
    *(.fini)
    *(.init_array*)
    *(.fini_array*)
    *(.preinit_array*)
    *(.eh_frame .eh_frame.*)
    *(.note.gnu.property)
    *(.note.gnu.build-id)
    *(.comment)
  }
}
