# cxl-tool.py — command-line options

This file describes each `argparse` option in `cxl-tool.py`: what it means, whether it takes a value, and what the tool does when you use it.

**Convention**

- **Flag** — no value; presence turns the option on (`action='store_true'`).
- **Option** — takes a string argument (often a device name, path, or mode). Empty default means “do nothing for this option.”

Most options can be combined in one invocation; the script runs the matching blocks **in a fixed order** (setup/build first, then topology, then run/login, and so on). Several flags each trigger their own action in sequence.

Requires a valid **`.vars.config`** in the current directory (or the fallback described under `--set-vars` / startup), except when using **`--set-vars`** alone (it exits after copying the config).

---

## General

| Option | Type | Help text | Behavior |
|--------|------|-----------|----------|
| `-v`, `--verbose` | Flag | show more message | Prints the parsed `args` dict, config load notes, and environment details. |
| `--set-vars` *file* | Option | choose a config file as .vars.config | Copies *file* to `./.vars.config` and **exits** (does not run other actions). Errors if *file* is missing. |

---

## QEMU run / topology

| Option | Type | Help text | Behavior |
|--------|------|-----------|----------|
| `-R`, `--run` | Flag | start qemu instance in background | Starts x86_64 QEMU with CXL topology and kernel from `.vars.config`. Uses `topo` from `-T` / `--create-topo` if set, else **RP1**. Runs in background per `run_qemu(..., run_direct=False)`. |
| `--run-direct` | Flag | start qemu instance | Same as `--run` but **`run_direct=True`** (foreground / direct attach behavior inside `run_qemu`). |
| `-T`, `--topo` *name* | Option | cxl topology to use | Selects topology: either a **named** built-in (resolved via `cxl.find_topology`) or, with `--raw`, a **literal** QEMU argument string. |
| `--raw` | Flag | The raw QEMU topology string. Only used with T/--topo | With `-T`, treats the `-T` value as raw QEMU `-device`/`-object` text instead of a topology name. **Requires** `-T`; otherwise argparse errors. |
| `-A`, `--accel` *mode* | Option | accel mode: kvm/tcg | Passed to `run_qemu` (default **`kvm`**). |
| `-E`, `--extra` *string* | Option | extra options when run qemu | Sets environment variable **`qemu_extra_opt`** to *string* for downstream QEMU launch logic. |
| `--create-topo` | Flag | use xml to generate topology | Reads **`.cxl-topology.xml`** under `cxl_test_tool_dir`, generates a QEMU topology string via `gen_cxl_topology`, and sets global **`topo`** for a subsequent run. |

---

## VM access / lifecycle

| Option | Type | Help text | Behavior |
|--------|------|-----------|----------|
| `--login` | Flag | login to the VM | SSH to the guest using `vm_usr` and `ssh_port` from config. |
| `--login-fm` | Flag | login to the FM VM | SSH with **`ssh_port + 1`** (FM guest). |
| `--poweroff`, `--shutdown` | Flag | poweroff the VM | Calls `shutdown_vm()` on the main guest. |
| `--poweroff-fm`, `--shutdown-fm` | Flag | poweroff the FM VM | `shutdown_vm(ssh_port=ssh_port+1)`. |
| `-C`, `--cmd` *shell* | Option | command to execute on VM | Runs *shell* on the guest via SSH; prints non-empty stdout. |

---

## Debugging

| Option | Type | Help text | Behavior |
|--------|------|-----------|----------|
| `--ndb` *string* | Option | gdb ndctl on VM | Ensures VM is up and `~/ndctl` exists; installs `gdb` in VM; runs `gdb_on_vm` with `gdb --args ~/ndctl/build/<subdir>/...` where the first word of *string* is the ndctl subdir (e.g. `cxl` for `cxl` binary). |
| `--qdb` | Flag | gdb qemu | Attaches GDB to the host `qemu-system` process (`process_id`); may lower `yama/ptrace_scope`. |
| `--kdb` | Flag | gdb kernel | If VM is running, runs `gdb ./vmlinux` under **`KERNEL_ROOT`** on the host (with SIGINT ignored during the session). |

---

## CXL / ndctl on the guest

| Option | Type | Help text | Behavior |
|--------|------|-----------|----------|
| `--install-ndctl` | Flag | install ndctl on VM | Clone/build ndctl on the guest (or host if bare metal) and verify `cxl`/`daxctl`/`ndctl` exist. |
| `--load-drv` | Flag | install cxl driver on VM | `cxl.load_driver()`. |
| `--unload-drv` | Flag | uninstall cxl driver on VM | `cxl.unload_driver()`. |
| `--create-region` *memdev* | Option | create cxl region | `cxl.create_region(memdev)`. |
| `--destroy-region` *region* | Option | destroy cxl region | `cxl.destroy_region(region)`. |
| `--cxl-pmem-test` *memdev* | Option | online pmem as system ram | Full workflow: ndctl, driver, pmem region/namespace, `daxctl` reconfigure + online RAM, `lsmem`. |
| `--cxl-vmem-test` *memdev* | Option | online vmem as system ram | Volatile CXL RAM path: region + `lsmem`. |
| `--create-dcR` *memdev* | Option | create a dc Region for a memdev | `cxl.create_dc_region(memdev)`. |
| `-M`, `--mode` *name* | Option | DC decoder mode (ram_a) | Sets **`dc_mode`** env to `dynamic_<name>` (default **`ram_a`**) for DC-related QEMU/device behavior. |

---

## DCD / QMP

| Option | Type | Help text | Behavior |
|--------|------|-----------|----------|
| `--dcd-test` *memdev* | Option | dcd test workflow for a memdev | Interactive DCD workflow: ndctl if needed, driver, DC region, extent QMP ops, optional DAX + system-ram. |
| `--issue-qmp` *file* | Option | Issue QMP command from a file to VM | Sends contents of *file* to the guest QMP port via `ncat` (`issue_qmp_cmd`). |

---

## Host setup: QEMU / kernel (x86_64)

| Option | Type | Help text | Behavior |
|--------|------|-----------|----------|
| `--setup-qemu` | Flag | setup qemu | Clone/configure QEMU under **`QEMU_ROOT`** using `qemu_url` / `qemu_branch` from environment. |
| `--setup-qemu-arm` | Flag | setup qemu for aarch64 | Prompts about non-upstream ARM CXL QEMU; then `setup_qemu` with **`aarch64-softmmu`**, `debug=False`. |
| `-BQ`, `--build-qemu` | Flag | build qemu | Builds QEMU in **`QEMU_ROOT`**. |
| `--setup-kernel` | Flag | setup kernel | Clone/configure Linux under **`KERNEL_ROOT`**. |
| `--setup-kernel-fm` | Flag | setup kernel for fm | `mctp.setup_kernel` on **`FM_KERNEL_ROOT`**. |
| `--kconfig` | Flag | configure kernel with menuconfig | `configure_kernel` on **`KERNEL_ROOT`**. |
| `-BK`, `--build-kernel` | Flag | build kernel | `build_kernel` on **`KERNEL_ROOT`**. |
| `--create-image` | Flag | create a qemu image | Builds/debootstrap guest image at **`QEMU_IMG`** (`create_qemu_image`). |

---

## MCTP / FM / libcxlmi

| Option | Type | Help text | Behavior |
|--------|------|-----------|----------|
| `--setup-mctp` | Flag | setup mctp test software | Runs **`test-workflows/mctp.sh`** setup path via `mctp_setup`. |
| `--setup-mctp-usb` | Flag | setup mctp test software for mctp over usb setup | Same pattern with **`mctp-usb.sh`**. |
| `--setup-mctp-fm` | Flag | setup mctp test software on FM | Temporarily shifts **`ssh_port` by +1**, runs `mctp.sh` on FM, then restores port. |
| `--try-mctp` | Flag | try mctp test | `mctp.try_fmapi_test()`. |
| `--test-fm` | Flag | run FMAPI test workflow | `mctp.run_fm_test()`. |
| `--test-libcxlmi` | Flag | run libcxlmi test workflow | Uses `libcxlmi_branch` / optional `libcxlmi_url` from config. |
| `--install-libcxlmi` | Flag | install libcxlmi on VM | Installs libcxlmi on main guest (branch/url from config). |
| `--install-libcxlmi-fm` | Flag | install libcxlmi on FM VM | Same on FM (**`ssh_port + 1`** during install). |
| `--start-vm` *mode* | Option | start vm with specified setup (regular, mctp) | If *mode* is **`mctp`**, `mctp.setup_vm_for_mctp()`. Otherwise starts QEMU like `--run` (topology from `-T` or **RP1**). |
| `--attach-fm` | Flag | Attach FM VM to an existing VM | Reads **`cxl_test_log_dir/topo0`**, checks required QEMU options, then starts a **second** QEMU (FM kernel/image, `port_offset=1`, `allow_multivm=True`) using **`-T` / `--topo`** for the FM client topology via `cxl.find_topology(args["topo"])`. |

---

## RAS / AER

| Option | Type | Help text | Behavior |
|--------|------|-----------|----------|
| `--install-ras-tools` | Flag | install ras related tool | Installs rasdaemon, mce-inject, mce-test, aer-inject (and related) on the guest. |
| `--inject-aer` *path* | Option | inject aer | `ras.inject_aer` with *path* (typically an aer-inject config file). |
| `--test-einj` *topo* | Option | workflow: testing aer inject with [topo] as parameter | `ras.test_aer_inject(topo)`. |

---

## AArch64 (ARM)

| Option | Type | Help text | Behavior |
|--------|------|-----------|----------|
| `--setup-kernel-arm` | Flag | configure and build kernel for aarch64 | `arm.setup_kernel_arm` on **`KERNEL_ROOT`**. |
| `--build-kernel-arm` | Flag | only build kernel for aarch64 | `arm.build_kernel_arm`. |
| `--start-arm` | Flag | start a VM for aarch64 | **`qemu-system-aarch64`** with topology (from `-T` or **RP1**), **`KERNEL_ROOT/arch/arm64/boot/Image`**, and **`BIOS`**. |

---

## See also

- Run **`./cxl-tool.py --help`** for the live list and short help strings.
- Paths, URLs, and ports come from **`.vars.config`** / environment (see main `README.md`).
