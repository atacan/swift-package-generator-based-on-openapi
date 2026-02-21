"""Manager to orchestrate all OpenAPI transformation operations.

This module coordinates the complete transformation pipeline:
1. Load the OpenAPI specification from a file
2. Apply all 6 transformation operations in sequence
3. Save the transformed specification back to a file
"""

from pathlib import Path

from bootstrapper.core.loader import load_spec
from bootstrapper.core.writer import write_spec
from bootstrapper.transformers.op1_null_anyof import remove_null_anyof
from bootstrapper.transformers.op2_const_enum import convert_const_to_enum
from bootstrapper.transformers.op3_float_to_number import convert_float_to_number
from bootstrapper.transformers.op4_nullable import convert_nullable_to_3_1
from bootstrapper.transformers.op5_format_fix import fix_byte_format
from bootstrapper.transformers.op6_clean_required import clean_required_arrays
from bootstrapper.transformers.op8_multipart_array_ref import fix_multipart_array_refs


def transform_spec(input_path: Path, output_path: Path) -> None:
    """
    Load OpenAPI spec, apply all transformations, and save the result.

    This function orchestrates the complete transformation pipeline:
    1. Load the spec from input_path (preserves format: JSON/YAML)
    2. Apply Op1: Remove null from anyOf arrays
    3. Apply Op2: Convert const to enum
    4. Apply Op3: Convert float to number
    5. Apply Op4: Convert nullable (3.0) to 3.1
    6. Apply Op5: Fix byte format
    7. Apply Op6: Clean required arrays
    8. Apply Op8: Fix multipart $ref-to-array properties
    9. Save the spec to output_path in the same format as the input

    Args:
        input_path: Path to the input OpenAPI specification file (.json, .yaml, or .yml)
        output_path: Path where the transformed specification will be written

    Raises:
        FileNotFoundError: If the input file doesn't exist
        ValueError: If the input file has an unsupported extension
        json.JSONDecodeError: If JSON parsing fails
        yaml.YAMLError: If YAML parsing fails
        IOError: If writing to output_path fails
    """
    # Step 1: Load the specification
    spec, file_format = load_spec(input_path)

    # Step 2-7: Apply all transformations in sequence
    spec = remove_null_anyof(spec)
    spec = convert_const_to_enum(spec)
    spec = convert_float_to_number(spec)
    spec = convert_nullable_to_3_1(spec)
    spec = fix_byte_format(spec)
    spec = clean_required_arrays(spec)
    spec = fix_multipart_array_refs(spec)

    # Step 9: Save the transformed specification
    write_spec(spec, output_path, file_format)
