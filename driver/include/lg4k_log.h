#ifndef LG4K_LOG_H
#define LG4K_LOG_H
/* Force-included into every source file (see Makefile). The vendor code logs
 * hundreds of status lines with bare printk(); route those through a switch
 * so the kernel log stays quiet unless `modprobe cx511h debug=1`. */
#include <linux/printk.h>
#include <linux/types.h>

extern bool lg4k_debug;

#define lg4k_printk(fmt, ...)                         \
	do {                                          \
		if (lg4k_debug)                       \
			printk(fmt, ##__VA_ARGS__);   \
	} while (0)
#endif
