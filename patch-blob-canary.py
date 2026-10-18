#!/usr/bin/env python3
"""Patch AverMediaLib_64.a for kernels >= 6.x on x86_64.

The blob was built against old kernels where the stack-protector canary lived
at the fixed per-CPU offset %gs:0x28. Modern kernels use __stack_chk_guard
instead, so %gs:0x28 is unmapped and every blob function oopses on entry.

Each canary access is rewritten in place (same length, no relocations):
  mov %gs:0x28,%rax  ->  mov $0,%rax ; nop      (canary = 0)
  xor %gs:0x28,%reg  ->  test %reg,%reg ; nop   (same ZF as the original xor)
Usage: patch-blob-canary.py IN.a OUT.a
"""
import re, sys

src, dst = sys.argv[1], sys.argv[2]
data = bytearray(open(src, 'rb').read())
TAIL = re.escape(b'\x25\x28\x00\x00\x00')
movs = xors = 0

for m in list(re.finditer(rb'\x65\x48([\x8b\x33])([\x04\x0c\x14\x1c\x34\x3c])' + TAIL, data)):
    op, modrm = m.group(1)[0], m.group(2)[0]
    reg = (modrm >> 3) & 7
    if op == 0x8b:
        if reg != 0:
            sys.exit(f'unexpected mov target reg {reg} at {m.start():#x}')
        new = b'\x48\xc7\xc0\x00\x00\x00\x00' + b'\x66\x90'          # mov $0,%rax; nop
        movs += 1
    else:
        new = bytes([0x48, 0x85, 0xc0 | (reg << 3) | reg]) + b'\x66\x0f\x1f\x44\x00\x00'  # test reg,reg; nopw
        xors += 1
    assert len(new) == 9
    data[m.start():m.end()] = new

left = len(re.findall(rb'\x65.{0,4}' + TAIL, data, re.S))
if left:
    sys.exit(f'{left} unrecognised %gs:0x28 references remain; not writing output')
open(dst, 'wb').write(data)
print(f'patched {movs} canary loads and {xors} canary checks')
