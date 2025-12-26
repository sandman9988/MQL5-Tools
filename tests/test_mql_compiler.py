import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools import mql_compiler as mc


def _make_fake_compiler(tmp_path: Path, exit_code: int = 0) -> Path:
    compiler = tmp_path / "fake_compiler.py"
    compiler.write_text(
        textwrap.dedent(
            """
            #!/usr/bin/env python
            import pathlib
            import sys


            def main():
                args = sys.argv[1:]
                compile_arg = next((a for a in args if a.startswith("/compile:")), None)
                out_arg = next((a for a in args if a.startswith("/out:")), None)
                if not compile_arg:
                    print("Missing /compile flag", file=sys.stderr)
                    return 2

                source = pathlib.Path(compile_arg.split(":", 1)[1])
                target = pathlib.Path(out_arg.split(":", 1)[1]) if out_arg else source.with_suffix(".ex5")
                target.write_text(f"compiled {{source.name}}")
                print("Compilation succeeded for", source)
                return {exit_code}


            if __name__ == "__main__":
                raise SystemExit(main())
            """
        )
        .format(exit_code=exit_code)
        .strip()
    )
    compiler.chmod(compiler.stat().st_mode | stat.S_IEXEC)
    return compiler


class MqlCompilerTests(unittest.TestCase):
    def test_build_command_supports_wine_and_extra_args(self) -> None:
        config = mc.CompilerConfig(
            compiler_path=Path("/opt/MetaTrader/MetaEditor64.exe"),
            wine=True,
            extra_args=("/q",),
        )
        command = config.build_command(Path("/tmp/script.mq5"), Path("/tmp/script.ex5"))

        self.assertEqual(command[0], "wine")
        self.assertIn("/compile:/tmp/script.mq5", command)
        self.assertIn("/out:/tmp/script.ex5", command)
        self.assertEqual(command[-1], "/q")

    def test_compile_source_with_fake_compiler(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            compiler = _make_fake_compiler(tmp_path)
            source = tmp_path / "sample.mq5"
            source.write_text("//+------------------------------------------------------------------+")

            result = mc.compile_source(source, compiler=compiler, extra_args=["/q"], timeout=10)

            self.assertTrue(result.succeeded)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(result.output_path.exists())
            self.assertIn("sample.mq5", result.stdout)
            self.assertIn("/q", " ".join(result.command))

    def test_compile_source_handles_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            compiler = _make_fake_compiler(tmp_path, exit_code=3)
            source = tmp_path / "fail.mq4"
            source.write_text("// failing script")
            result = mc.compile_source(source, compiler=compiler, timeout=5)

            self.assertFalse(result.succeeded)
            self.assertEqual(result.returncode, 3)
            # Output path should still be reported even if compilation fails.
            self.assertEqual(result.output_path.suffix, ".ex4")

    def test_compile_source_uses_env_variable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            compiler = _make_fake_compiler(tmp_path)
            source = tmp_path / "env_based.mq5"
            source.write_text("// env based")

            original = os.environ.get(mc.MQL_COMPILER_ENV)
            os.environ[mc.MQL_COMPILER_ENV] = str(compiler)
            try:
                result = mc.compile_source(source, timeout=5)
            finally:
                if original is None:
                    os.environ.pop(mc.MQL_COMPILER_ENV, None)
                else:
                    os.environ[mc.MQL_COMPILER_ENV] = original

            self.assertTrue(result.succeeded)
            self.assertEqual(result.output_path.suffix, ".ex5")

    def test_missing_source_raises(self) -> None:
        missing = Path("/nonexistent/path.mq5")
        with self.assertRaises(FileNotFoundError):
            mc.compile_source(missing, compiler=Path("/opt/fake.exe"))

    def test_cli_invocation_runs_compiler(self) -> None:
        repo_root = Path(__file__).parent.parent
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            compiler = _make_fake_compiler(tmp_path)
            source = tmp_path / "cli_test.mq5"
            source.write_text("// cli invocation")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.mql_compiler",
                    str(source),
                    "--compiler",
                    str(compiler),
                    "--timeout",
                    "10",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
            self.assertIn("Command:", result.stdout)
            self.assertTrue((tmp_path / "cli_test.ex5").exists())

    def test_parse_args_with_minimal_arguments(self) -> None:
        args = mc.parse_args(["test.mq5"])
        self.assertEqual(args.source, Path("test.mq5"))
        self.assertIsNone(args.output)
        self.assertIsNone(args.compiler)
        self.assertFalse(args.wine)
        self.assertEqual(args.timeout, 120)
        self.assertEqual(args.extra_arg, [])

    def test_parse_args_with_all_arguments(self) -> None:
        args = mc.parse_args([
            "source.mq4",
            "--output", "output.ex4",
            "--compiler", "/path/to/compiler.exe",
            "--wine",
            "--timeout", "60",
            "--extra-arg", "/q",
            "--extra-arg", "/v",
        ])
        self.assertEqual(args.source, Path("source.mq4"))
        self.assertEqual(args.output, Path("output.ex4"))
        self.assertEqual(args.compiler, Path("/path/to/compiler.exe"))
        self.assertTrue(args.wine)
        self.assertEqual(args.timeout, 60)
        self.assertEqual(args.extra_arg, ["/q", "/v"])

    def test_parse_args_default_timeout_value(self) -> None:
        args = mc.parse_args(["script.mq5"])
        self.assertEqual(args.timeout, 120)

    def test_parse_args_short_output_flag(self) -> None:
        args = mc.parse_args(["script.mq5", "-o", "custom.ex5"])
        self.assertEqual(args.output, Path("custom.ex5"))

    def test_parse_args_help_text(self) -> None:
        # Test that help text can be generated without error
        # This verifies the parser is configured correctly
        with self.assertRaises(SystemExit) as cm:
            mc.parse_args(["--help"])
        # --help should exit with code 0
        self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
