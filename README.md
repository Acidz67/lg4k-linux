# Live Gamer 4K (GC573) Linux driver

A Linux driver for the AVerMedia **Live Gamer 4K (GC573)** PCIe capture card, updated to build and run on modern kernels (tested on 7.2) and packaged with DKMS so it rebuilds itself on kernel updates.

This is a fork of [derrod/lg4k-linux](https://github.com/derrod/lg4k-linux), which adapted AVerMedia's Linux driver for the closely related [CL511HN](https://www.avermedia.com/professional/product/cl511hn/overview) ([original download](http://storage.avermedia.com/web_release_www/CL511HN/Generic_Ubuntu_CL511HN_Drv_1.0.0031.zip)). That project hasn't been updated since 2020 and no longer builds or runs on current kernels.

## Status

Tested on CachyOS with kernel `7.2.10-cachyos` (Clang + ThinLTO) on an AMD Ryzen system. It also builds for Arch's stock `7.2.11-arch` kernel (GCC), but it hasn't been run on that kernel yet.

| Feature | Status |
|---|---|
| Video capture (V4L2, e.g. OBS) | ✅ Works (tested at 2560×1440) |
| Audio capture (ALSA / PipeWire) | ✅ Works (16-bit, 48 kHz stereo) |
| HDMI signal detection | ✅ Works |
| Loads automatically at boot | ✅ Works |
| Rebuilds on kernel updates (DKMS) | ✅ Works |
| 4K60 / HDR input | ❓ Untested; may not work on the LG4K |
| HDMI pass-through output | ✅ Works |
| Suspend / resume | ❓ Untested |
| Scaling | ❌ Capture resolution must match the input resolution |
| "No signal" placeholder image | ❌ No frames are delivered when nothing is plugged in |
| RGB24 pixel format | ❌ Use YUYV (the default) |
| RGB LEDs | ❌ Not supported; they keep flashing red |

## Requirements

- An x86_64 machine with a GC573 (PCI ID `1461:0054`)
- Kernel headers for every kernel you run
- `dkms`
- Python 3, only if you need to re-run `patch-blob-canary.py` (the patched library is already committed)

> **Intel CPUs (Tiger Lake / 11th gen and newer):** the closed-source part of the driver isn't built for Indirect Branch Tracking (IBT). If the module crashes on load with a "Missing ENDBR" / control-protection error, add `ibt=off` to your kernel command line. AMD CPUs aren't affected.

## Installation

### Arch Linux / CachyOS / Arch-based distros

```bash
git clone https://github.com/Acidz67/lg4k-linux.git
cd lg4k-linux
sudo ./install-arch.sh
```

The script:

1. Installs `dkms` and the headers for each installed kernel (`linux` → `linux-headers`, `linux-cachyos` → `linux-cachyos-headers`, and so on)
2. Copies the source to `/usr/src/lg4k-1.0.0031` and registers it with DKMS
3. Builds and installs the module for every installed kernel
4. Loads the module (`cx511h`)

If an older version of the driver is already loaded and in use (OBS or PipeWire has it open), use `--no-load` and reboot:

```bash
sudo ./install-arch.sh --no-load
sudo reboot
```

### Other distributions (untested)

Install DKMS and your kernel headers with your package manager, then:

```bash
sudo mkdir -p /usr/src/lg4k-1.0.0031
sudo cp -r driver AverMediaLib_64.a dkms.conf /usr/src/lg4k-1.0.0031/
sudo dkms add -m lg4k -v 1.0.0031
sudo dkms install -m lg4k -v 1.0.0031
sudo modprobe cx511h
```

The build picks the compiler automatically: if the kernel was built with Clang (like CachyOS), the module is built with `LLVM=1`.

> Don't combine this with the old `build.sh` / `install.sh` scripts. They install a second copy of the module outside DKMS.

### Checking that it worked

```bash
ls /dev/video*                      # the card shows up as a video device
v4l2-ctl -d /dev/video0 --info      # "Card type: AVerMedia CL511H"
cat /proc/asound/cards              # "AVerMedia CL511H"
```

The card identifies itself as **CL511H**. That's expected; it's the name from the original AVerMedia driver.

## Using it in OBS

**Video:** add a **Video Capture Device (V4L2)** source and select **AVerMedia CL511H**. Set the resolution to match what your source is sending. The card can't scale, so a mismatch gives a black or frozen picture.

**Audio:** add an **Audio Input Capture (PipeWire/PulseAudio)** source and select **AVerMedia CL511H Stereo**. To hear the source through your speakers or headset while you play, open the Audio Mixer, click ⋮ → **Advanced Audio Properties**, and set the source to **Monitor and Output**.

The card only allows one program at a time to capture video.

## Updating

Kernel updates need no action: DKMS rebuilds the module automatically when a new kernel is installed.

To update the driver itself:

```bash
cd lg4k-linux
git pull
sudo ./install-arch.sh --no-load
sudo reboot
```

## Uninstalling

```bash
sudo modprobe -r cx511h
sudo dkms remove -m lg4k -v 1.0.0031 --all
sudo rm -rf /usr/src/lg4k-1.0.0031
```

## Troubleshooting

**No `/dev/video0`, or the module fails to load:** check the kernel log:

```bash
journalctl -k -b | grep -A40 board_probe
```

A successful load contains `board_probe subsystem_id=5730` and `board_probe=0`.

**Verbose logging:** the driver is quiet by default; only errors and warnings reach the kernel log. To turn on detailed status messages:

```bash
echo 1 | sudo tee /sys/module/cx511h/parameters/debug   # on
echo 0 | sudo tee /sys/module/cx511h/parameters/debug   # off
```

or load it with `sudo modprobe cx511h debug=1`.

**Black screen in OBS with a source connected:** check that the OBS resolution matches the source. If it does, try setting the source to 1080p60 and turning HDR off.

**DKMS build fails after a kernel update:** kernel APIs change over time, so a future kernel may need further porting. Run `sudo dkms status` and check `/var/lib/dkms/lg4k/1.0.0031/build/make.log`, then open an issue with the error.

## What changed from upstream

<details>
<summary>Kernel API updates</summary>

- `EXTRA_CFLAGS` / `EXTRA_LDFLAGS` → `ccflags-y` / `ldflags-y` (the old variables were removed from kbuild)
- Builds with `LLVM=1` automatically on Clang-built kernels; adds a `.cmd` stub so modpost accepts the prebuilt library
- ALSA: managed vmalloc buffers replace the removed `snd_pcm_lib_*_vmalloc_*` helpers
- videobuf2: removed `wait_prepare` / `wait_finish` ops (the queue lock is used instead)
- V4L2: `VIDIOC_G_CTRL` / `S_CTRL` / `QUERYCTRL` implemented via the extended control ops; `VFL_TYPE_VIDEO`; new `v4l2_fh_add()` / `v4l2_fh_del()` signatures
- `dma_set_mask()`, `timer_container_of()`, `timer_delete_sync()`, `strscpy()` / `strscpy_pad()`, `<linux/stdarg.h>`
- Dropped the unexported `vfs_stat()` call; `sys_fclose(NULL)` no longer crashes

</details>

<details>
<summary>Runtime fixes</summary>

- **Stack-protector crash in the closed-source library.** `AverMediaLib_64.a` was compiled for kernels that kept the stack canary at `%gs:0x28`. Modern kernels don't, so every library function crashed on entry. `patch-blob-canary.py` rewrites the 40 canary loads and 40 checks in place. The canary inside the library is now a constant 0, which still catches stack overwrites that change it but is weaker than normal protection. The rest of the driver and the kernel are unaffected.
- **HDMI receiver never attached.** The driver found the ITE6805 chip driver by walking past the end of an empty array placed in the same linker section. That array had no terminator and was removed entirely by Clang LTO. The driver is now listed explicitly.
- **"Scheduling while atomic" and preempt-count corruption.** The library sleeps while holding its I2C lock. On preemptible kernels that corrupts per-CPU preempt counts and can deadlock. Process-context locks are now backed by a mutex. The interrupt-context lock is unchanged.
- **Half-speed audio.** The hardware delivers 16-bit audio and the driver copies it through without conversion, but it also advertised 24-bit. PipeWire chose 24-bit and the audio played at half speed. Only 16-bit is advertised now.

</details>

<details>
<summary>Quality of life</summary>

- DKMS packaging (`dkms.conf`) and an Arch install script (`install-arch.sh`)
- Routine status logging is behind a `debug` module parameter (it used to write hundreds of lines to the kernel log)

</details>

## About the closed-source library

`AverMediaLib_64.a` is AVerMedia's prebuilt library for the HDMI receiver and FPGA control. It runs inside the kernel and its source isn't available. This repository ships a binary-patched copy (see above); `patch-blob-canary.py` documents the exact changes, and the unmodified original is in the git history. Loading the module marks the kernel as tainted (out-of-tree, unsigned), which is normal for third-party drivers.

## Credits

- AVerMedia: original CL511HN Linux driver
- [derrod](https://github.com/derrod/lg4k-linux): adapting it for the Live Gamer 4K
