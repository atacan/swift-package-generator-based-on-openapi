"""Manager to orchestrate all OpenAPI transformation operations.

This module coordinates the complete transformation pipeline:
1. Load the OpenAPI specification from a file
2. Apply all transformation operations in sequence
3. Save the transformed specification back to a file
"""

from pathlib import Path
from typing import Callable

from rich.console import Console

from bootstrapper.core.loader import load_spec
from bootstrapper.core.writer import write_spec
from bootstrapper.transformers.op1_null_anyof import remove_null_anyof
from bootstrapper.transformers.op2_const_enum import convert_const_to_enum
from bootstrapper.transformers.op3_float_to_number import convert_float_to_number
from bootstrapper.transformers.op4_nullable import convert_nullable_to_3_1
from bootstrapper.transformers.op5_format_fix import fix_byte_format
from bootstrapper.transformers.op6_clean_required import clean_required_arrays
from bootstrapper.transformers.op8_multipart_array_ref import fix_multipart_array_refs

_PIPELINE: list[tuple[str, Callable[[dict], dict]]] = [
    ("op1: remove null from anyOf/oneOf", remove_null_anyof),
    ("op2: convert const to enum", convert_const_to_enum),
    ("op3: convert float to number", convert_float_to_number),
    ("op4: convert nullable to OpenAPI 3.1", convert_nullable_to_3_1),
    ("op5: fix byte format", fix_byte_format),
    ("op6: clean required arrays", clean_required_arrays),
    ("op8: fix multipart $ref-to-array", fix_multipart_array_refs),
]


def transform_spec(input_path: Path, output_path: Path, console: Console | None = None) -> None:
    """
    Load OpenAPI spec, apply all transformations, and save the result.

    Args:
        input_path: Path to the input OpenAPI specification file (.json, .yaml, or .yml)
        output_path: Path where the transformed specification will be written
        console: Optional Rich Console for progress output

    Raises:
        FileNotFoundError: If the input file doesn't exist
        ValueError: If the input file has an unsupported extension
        json.JSONDecodeError: If JSON parsing fails
        yaml.YAMLError: If YAML parsing fails
        IOError: If writing to output_path fails
    """
    spec, file_format = load_spec(input_path)

    for label, transformer in _PIPELINE:
        if console:
            console.print(f"  [dim]→ {label}[/dim]")
        spec = transformer(spec)

    write_spec(spec, output_path, file_format)
