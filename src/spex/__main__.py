# SPDX-FileCopyrightText: 2023 Samsung Electronics Co., Ltd
#
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import sys
import textwrap
from pathlib import Path
from typing import List

from spex.jsonspec.lint import Code
from spex.logging import ULog, logger
from spex.parse import ParserArgs, parse_spec


def arg_input(arg: str) -> Path:
    p = Path(arg)
    if not p.exists():
        raise RuntimeError(f"no file at '{p}'")
    elif not p.is_file():
        raise RuntimeError(f"path '{p}' exists, but is not a file")
    return p


def arg_output(arg: str) -> Path:
    p = Path(arg)
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
    if not p.is_dir():
        raise RuntimeError("output must be a directory (or omitted)")

    return p


def arg_lintcode(arg: str) -> List[Code]:
    return [Code[c.strip().upper()] for c in arg.split(",")]


class CliParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write(f"error: {message}\n")
        self.print_help()
        sys.exit(2)


def main():
    lint_codes = "\n".join(f"      * {entry.name}  - {entry.value}" for entry in Code)
    epilog = textwrap.dedent(
        f"""
    Notes:
    ~~~~~~
    * Linting:
      During production of the NVMe-model, a number of linting codes are raised.
      These signify potential and definite issues encountered when parsing the
      source HTML model, in turn derived from the docx specification document.

      You may choose to ignore classes of errors during processing.
      For instance, to ignore lint errors of code T1000 and T1001, add the
      following to your command: `--lint-ignore=T1000,T1001`.

      The linting codes, and their general meaning, are as follows:
      ---
{lint_codes}
      ---
    * output:
      if `output` is a directory, then any output(s) generated from processing
      (NVMe (JSON) models, HTML models, CSS files) will be placed in the
      specified directory. If `output` is omitted, files will be placed into the
      current working directory.
    """
    )
    parser = CliParser(
        description="Extract data-structures from .docx spec or HTML model",
        epilog=epilog,
        prog="spex",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--skip-figure-on-error",
        default=False,
        dest="skip_fig_on_error",
        action="store_true",
        help="If processing a figure fails, do not abort, but skip it and continue processing the remaining figures",
    )
    parser.add_argument(
        "input",
        nargs="+",
        type=arg_input,
        help="One or more .docx specifications or HTML models to extract data-structures from",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=arg_output,
        default=None,
        help="path to directory where the resulting file(s) should be stored.",
    )
    parser.add_argument("--lint-ignore", type=arg_lintcode, default=[])

    args = parser.parse_args()

    # if no explicit output directory is specified, use the current working directory
    if args.output is None:
        args.output = Path.cwd()

    pargs = ParserArgs(
        output_dir=args.output or Path.cwd(),
        skip_fig_on_error=args.skip_fig_on_error,
        lint_codes_ignore=args.lint_ignore,
    )

    try:
        for spec in args.input:
            logger.log(ULog.INFO, f"parsing '{spec}'...")
            if spec.suffix == ".json":
                # lint code filtering is applied at the point of writing the lint errors
                # into the resulting NVMe (JSON) model.
                sys.stderr.write(
                    "cannot operate on NVMe model (JSON), requires the HTML model or docx spec as input\n"
                )
                sys.stderr.flush()
                sys.exit(1)

            if spec.suffix not in (".html", ".docx"):
                sys.stderr.write(
                    f"invalid input file ({spec!s}), requires a HTML model or the docx specification file\n"
                )
                sys.stderr.flush()
                sys.exit(1)
            for _ in parse_spec(spec, pargs, yield_progress=False):
                pass
    except Exception:
        logger.exception("unhandled exception bubbled up to top-level")

        logger.log(
            ULog.ERROR,
            "\n  ".join(
                [
                    "Program exited in error!",
                    "",
                    "This typically happens if spex failed to parse one or more figures.",
                    "Check the log messages above to see which figures are causing errors.",
                    "",
                    "If you believe Spex *should* be able to parse this figure - and that",
                    "it is not simply a matter of changing to the figure to follow conventions",
                    "then perhaps a bug report for Spex is in order.",
                    "When filing the bug report, please attach the `spex.log` file which resides",
                    "in this directory.",
                    "Note that the `spex.log` file is rewritten on each execution",
                ]
            ),
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
