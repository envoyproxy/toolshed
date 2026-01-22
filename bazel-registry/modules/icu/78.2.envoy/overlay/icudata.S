    .globl icudt78_dat
    .section .rodata,"a",@progbits
    .balign 16
    .type icudt78_dat, @object
icudt78_dat:
    .incbin "source/data/in/icudt78l.dat"
    .size icudt78_dat, .-icudt78_dat
