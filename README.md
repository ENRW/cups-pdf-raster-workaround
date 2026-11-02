# CUPS says “completed”, but nothing prints

**English** · [Deutsch](README.de.md)

A documented PDF-to-URF workaround for a **HP OfficeJet Pro 8730** on **CUPS 2.x**, including correct long-edge duplex printing.

The misleading symptom: a PDF job disappears from the queue as successful, **no paper comes out**, and there is **no useful failure message**. In the investigated case, CUPS counted nine completed pages while the printer itself reported zero printed pages and zero sheets.

Rendering the pages on the computer and sending **URF raster data** solved the tested case. The precise PDF feature or firmware behavior causing the original failure remains unknown. This repository documents a tested workaround, not a universal printer fix.

## What changes

The existing printer queue keeps its address, paper sizes, color options and duplex settings. Its native PDF pass-through rule is removed, leaving the existing URF route available:

```text
Before: PDF -> pdftopdf -> PDF sent to the printer
After:  PDF -> pdftopdf -> gstoraster -> URF sent to the printer
```

The host renders the page content before transmission. In this setup, normal quality produced 300 dpi and high quality 600 dpi. Long-edge orientation was checked on an actual printed sheet.

The helper supports only the narrow PPD layout used in this case: native PDF pass-through, URF pass-through, and optionally JPEG pass-through. It refuses other output routes rather than guessing. It does not install packages, change CUPS, contact a printer, or print anything.

## Before applying it

- Use a **CUPS 2.x queue with a PPD** and a printer that actually supports `image/urf`. This is not a CUPS 3 / Printer Application configuration guide.
- Verify that host-side rendering works. Raster output still uses the host PDF filters; it cannot repair a broken `pdftopdf` installation.
- The printer must be reachable and able to print an image. This workaround does not address paper, ink, authentication or connection problems.
- Python 3.10+ and the usual CUPS tools are needed. The Python helper has no third-party dependencies.

There was also an earlier, separate `libcupsfilters` regression on this machine. See [the case study](CASE-STUDY.md#separate-host-filter-regressions) before treating every blank-page or duplex problem as the same issue.

## Prepare and inspect a change

Run these commands from this repository. Replace `YOUR_QUEUE` with the queue name from `lpstat -p`, and choose a local test PDF. The work directory is a private, persistent backup directory in your home folder.

```bash
PRINTER='YOUR_QUEUE'
PDF='/path/to/test.pdf'
CUPS_WORK_DIR="$HOME/cups-raster-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$CUPS_WORK_DIR"

curl --fail --show-error \
  "http://localhost:631/printers/${PRINTER}.ppd" \
  --output "$CUPS_WORK_DIR/original.ppd"

python3 prepare_ppd.py "$CUPS_WORK_DIR/original.ppd" --check
python3 prepare_ppd.py \
  "$CUPS_WORK_DIR/original.ppd" "$CUPS_WORK_DIR/raster.ppd"

cupstestppd -v "$CUPS_WORK_DIR/original.ppd" > "$CUPS_WORK_DIR/original-validation.txt"
cupstestppd -v "$CUPS_WORK_DIR/raster.ppd" > "$CUPS_WORK_DIR/raster-validation.txt"
cupsfilter --list-filters -p "$CUPS_WORK_DIR/raster.ppd" -e \
  -i application/pdf -m "printer/$PRINTER" "$PDF"
```

Stop if preparation or filter-path inspection fails. The helper prints the exact change and refuses to overwrite an existing output file. Its compatibility check is deliberately limited. Inspect both validator reports: automatically generated PPDs may already have conformance errors. In this case, both reports contained the same pre-existing missing-translation and overlong-`ShortNickName` findings; there were no new failures. Investigate new findings and any structural or filter errors before installing. A valid route must render to URF; in the tested installation the filter list was `pdftopdf`, then `gstoraster`.

The removed rule in this case was:

```text
*cupsFilter2: "application/vnd.cups-pdf application/pdf 10 -"
```

The existing `image/urf` rule and **all duplex/back-side settings are preserved**. Do not replace `cupsBackSide: Rotated` with `Normal` just to compensate for an upside-down test; see the conversion trap below.

## Apply, test, roll back

Once the prepared PPD and filter route are correct, apply it to the existing queue:

```bash
sudo lpadmin -p "$PRINTER" -P "$CUPS_WORK_DIR/raster.ppd"
```

The following command really prints the first two pages, normally on one sheet. Use an appropriate paper size for your printer:

```bash
lp -d "$PRINTER" -n 1 -P 1-2 \
  -o media=A4 -o sides=two-sided-long-edge "$PDF"
```

Check that both pages are present and upright when turning the sheet like a book. Keep using this configured queue in your PDF viewers; an independently discovered printer destination may use another path.

Rollback uses your own original PPD:

```bash
sudo lpadmin -p "$PRINTER" -P "$CUPS_WORK_DIR/original.ppd"
```

The queue configuration persists across restarts. Recreating the queue with `-m everywhere` can regenerate the PPD and undo the workaround. Keep the backup. Raster printing may use more processing time and network bandwidth.

## A trap: a “raster test” can become PDF again

Sending a pre-rendered `.urf` file to the **old** queue did not guarantee raster transmission. CUPS selected `pwgtopdf -> pdftopdf` and sent PDF again. A back page already oriented for raster transport then printed upside down.

With the modified queue, that native PDF destination is gone. In our tests, direct URF transmission and the final automatic PDF-to-URF queue both printed successfully. Preserve the printer's declared raster back-side convention and verify the actual filter route.

## Diagnose the silent failure

Compare CUPS with the **device's own** counters, and check the physical output. “Completed” alone did not prove that printing had happened.

The included IPP test is read-only. Set the actual IPP printer URI, not the localhost CUPS queue URI:

```bash
ipptool -T 10 -tv 'ipp://YOUR_PRINTER/ipp/print' get-printer-jobs.test
```

Some printers do not retain history or provide reliable counters. The test deliberately does not request usernames or document titles, but inspect any output before sharing it. Never attach a real PPD or print-spool document without checking for private identifiers and document content.

## Evidence, limitations and contributing

See [CASE-STUDY.md](CASE-STUDY.md) for the tested versions, measurements, rejected hypotheses, and related upstream issues. The original document is not distributed. The Python tests use synthetic PPD snippets; they test the helper, not firmware compatibility.

```bash
python3 -m unittest -v
```

Reports in English or German are welcome. Include the printer model, CUPS/filter versions, relevant filter rules, the chosen filter route, and whether the device actually printed. Redact local addresses, serial numbers, usernames and document contents. Do not infer that every printer has the same internal defect.

Technical references: [CUPS filter rules and back-side conventions](https://openprinting.github.io/cups/doc/spec-ppd.html#cupsFilter2), [queue configuration with lpadmin](https://openprinting.github.io/cups/doc/man-lpadmin.html).

[MIT license](LICENSE).
