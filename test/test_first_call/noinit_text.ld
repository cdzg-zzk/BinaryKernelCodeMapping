OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)

PHDRS {
    text    PT_LOAD    FLAGS(0x5) FILEHDR PHDRS; /* Map ELF/PHDRs in first RX segment */
    data    PT_LOAD    FLAGS(0x6); /* PF_R | PF_W */
    dynamic PT_DYNAMIC FLAGS(0x6);
}

SECTIONS
{
    /* Place headers inside the first RX segment. */
    . = 0x1000;

    . = ALIGN(0x1000);
    .text :
    {
        *(.text .text.*)
    } :text

    . = ALIGN(0x1000);
    .rodata :
    {
        *(.rodata .rodata.*)
        *(.eh_frame .eh_frame.*)
        *(.note.gnu.property)
        *(.note.gnu.build-id)
    } :text

    . = ALIGN(0x1000);
    .dynamic : { *(.dynamic) } :data :dynamic

    . = ALIGN(0x1000);
    .dynsym   : { *(.dynsym)   } :data
    .dynstr   : { *(.dynstr)   } :data
    .gnu.hash : { *(.gnu.hash) } :data
    .hash     : { *(.hash)     } :data
    .rela.dyn : { *(.rela.dyn) } :data
    .rela.plt : { *(.rela.plt) } :data
    .got.plt  : { *(.got.plt) *(.igot.plt) } :data
    .got      : { *(.got) *(.igot)         } :data

    /* Drop any startup/teardown sections to avoid touching .text before first call. */
    /DISCARD/ :
    {
        *(.init)
        *(.fini)
        *(.init_array*)
        *(.fini_array*)
        *(.comment)
    }
}
