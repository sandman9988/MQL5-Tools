from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


MQL_COMPILER_ENV = "MQL_COMPILER"


def _default_output_path(source: Path) -> Path:
    suffix = ".ex4" if source.suffix.lower() == ".mq4" else ".ex5"
    return source.with_suffix(suffix)


@dataclass
class CompilerConfig:
    """Configuration options for invoking the MetaTrader compiler."""

    compiler_path: Path
    wine: bool = False
    timeout: int = 120
    extra_args: Sequence[str] = field(default_factory=tuple)

    @classmethod
    def from_env(
        cls, *, wine: bool = False, timeout: int = 120, extra_args: Sequence[str] | None = None
    ) -> "CompilerConfig":
        compiler = os.getenv(MQL_COMPILER_ENV)
        if not compiler:
            raise ValueError(
                f"Set {MQL_COMPILER_ENV} to the MetaEditor/MetaTrader compiler executable."
            )
        return cls(
            compiler_path=Path(compiler),
            wine=wine,
            timeout=timeout,
            extra_args=tuple(extra_args or ()),
        )

    def build_command(self, source: Path, output: Optional[Path] = None) -> List[str]:
        target = output or _default_output_path(source)
        command: List[str] = []
        if self.wine:
            command.append("wine")
        command.append(str(self.compiler_path))
        command.append(f"/compile:{source}")
        command.append(f"/out:{target}")
        command.extend(self.extra_args)
        return command


@dataclass
class CompilerResult:
    command: List[str]
    returncode: int
    stdout: str
    stderr: str
    output_path: Path

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


def compile_source(
    source: Path,
    *,
    compiler: Path | None = None,
    output: Path | None = None,
    wine: bool = False,
    timeout: int = 120,
    extra_args: Optional[Iterable[str]] = None,
) -> CompilerResult:
    """
    Compile a .mq4/.mq5 file using a locally installed MetaTrader compiler.

    The compiler path can be provided explicitly or via the MQL_COMPILER environment
    variable. When running under Wine, set `wine=True` and ensure the compiler path
    points to the Windows executable.
    """

    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    compiler_path = compiler or os.getenv(MQL_COMPILER_ENV)
    if not compiler_path:
        raise FileNotFoundError("Compiler path not provided and MQL_COMPILER is not set.")

    config = CompilerConfig(
        compiler_path=Path(compiler_path),
        wine=wine,
        timeout=timeout,
        extra_args=tuple(extra_args or ()),
    )

    if not config.compiler_path.exists():
        raise FileNotFoundError(f"Compiler executable not found: {config.compiler_path}")

    target = output or _default_output_path(source)
    command = config.build_command(source, target)
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=config.timeout,
        check=False,
    )
    return CompilerResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        output_path=target,
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile MQL4/MQL5 sources with a locally installed MetaTrader compiler."
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Path to the .mq4/.mq5 file to compile.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Destination for the compiled output. Defaults to .ex4/.ex5 alongside the source.",
    )
    parser.add_argument(
        "--compiler",
        type=Path,
        help=f"Path to the compiler executable. Falls back to the {MQL_COMPILER_ENV} env var.",
    )
    parser.add_argument(
        "--wine",
        action="store_true",
        help="Prefix the compiler command with wine (useful on Linux when the compiler is a Windows binary).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout (in seconds) before aborting the compiler process.",
    )
    parser.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        help="Additional arguments to pass directly to the compiler.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    result = compile_source(
        args.source,
        compiler=args.compiler,
        output=args.output,
        wine=args.wine,
        timeout=args.timeout,
        extra_args=args.extra_arg,
    )

    print("Command:", " ".join(result.command))
    print("Return code:", result.returncode)
    print("Output file:", result.output_path)
    if result.stdout:
        print("stdout:\n", result.stdout)
    if result.stderr:
        print("stderr:\n", result.stderr)

    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
