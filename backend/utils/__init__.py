"""VisionOps AI — Utilities Package.

Reusable low-level utilities shared across the entire backend.
These are generic primitives without AI, business, API, or database logic.
"""

# ---------------------------------------------------------------------------
# csv_utils
# ---------------------------------------------------------------------------
from backend.utils.csv_utils import (
    append_rows,
    backup_csv,
    check_headers,
    csv_exists,
    detect_delimiter,
    export_csv,
    read_csv,
    update_rows,
    validate_csv,
    write_csv,
)

# ---------------------------------------------------------------------------
# json_utils
# ---------------------------------------------------------------------------
from backend.utils.json_utils import (
    deep_update,
    handle_malformed_json,
    merge_json,
    pretty_print,
    read_json,
    safe_deserialize,
    safe_serialize,
    validate_json,
    write_json,
)

# ---------------------------------------------------------------------------
# file_utils
# ---------------------------------------------------------------------------
from backend.utils.file_utils import (
    copy_file,
    create_directory,
    delete_file,
    directory_hash,
    directory_size,
    ensure_directory,
    file_exists,
    file_hash,
    file_size,
    is_empty_directory,
    list_directories,
    list_files,
    move_file,
    rename_file,
    safe_path,
    temporary_file,
)

# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------
from backend.utils.validation import (
    validate_directory,
    validate_email,
    validate_extension,
    validate_file_path,
    validate_filename,
    validate_ip,
    validate_numeric_range,
    validate_port,
    validate_required_values,
    validate_url,
    validate_uuid,
)

# ---------------------------------------------------------------------------
# timer
# ---------------------------------------------------------------------------
from backend.utils.timer import (
    AsyncTimer,
    Timer,
    timeit,
)

# ---------------------------------------------------------------------------
# date_utils
# ---------------------------------------------------------------------------
from backend.utils.date_utils import (
    datetime_to_timestamp,
    format_duration,
    format_iso,
    local_to_utc,
    now_local,
    now_utc,
    time_difference,
    timestamp_to_datetime,
    utc_to_local,
)

# ---------------------------------------------------------------------------
# id_generator
# ---------------------------------------------------------------------------
from backend.utils.id_generator import (
    generate_correlation_id,
    generate_job_id,
    generate_report_id,
    generate_session_id,
    generate_timestamp_id,
    generate_trace_id,
    generate_tracking_id,
    generate_uuid4,
    generate_worker_id,
)

# ---------------------------------------------------------------------------
# math_utils
# ---------------------------------------------------------------------------
from backend.utils.math_utils import (
    average,
    clamp,
    distance,
    median,
    min_max,
    normalize,
    percentage,
    round_to,
    safe_division,
    standard_deviation,
    variance,
)

# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------
__all__ = [
    # csv_utils
    "append_rows",
    "backup_csv",
    "check_headers",
    "csv_exists",
    "detect_delimiter",
    "export_csv",
    "read_csv",
    "update_rows",
    "validate_csv",
    "write_csv",
    # json_utils
    "deep_update",
    "handle_malformed_json",
    "merge_json",
    "pretty_print",
    "read_json",
    "safe_deserialize",
    "safe_serialize",
    "validate_json",
    "write_json",
    # file_utils
    "copy_file",
    "create_directory",
    "delete_file",
    "directory_hash",
    "directory_size",
    "ensure_directory",
    "file_exists",
    "file_hash",
    "file_size",
    "is_empty_directory",
    "list_directories",
    "list_files",
    "move_file",
    "rename_file",
    "safe_path",
    "temporary_file",
    # validation
    "validate_directory",
    "validate_email",
    "validate_extension",
    "validate_file_path",
    "validate_filename",
    "validate_ip",
    "validate_numeric_range",
    "validate_port",
    "validate_required_values",
    "validate_url",
    "validate_uuid",
    # timer
    "AsyncTimer",
    "Timer",
    "timeit",
    # date_utils
    "datetime_to_timestamp",
    "format_duration",
    "format_iso",
    "local_to_utc",
    "now_local",
    "now_utc",
    "time_difference",
    "timestamp_to_datetime",
    "utc_to_local",
    # id_generator
    "generate_correlation_id",
    "generate_job_id",
    "generate_report_id",
    "generate_session_id",
    "generate_timestamp_id",
    "generate_trace_id",
    "generate_tracking_id",
    "generate_uuid4",
    "generate_worker_id",
    # math_utils",
    "average",
    "clamp",
    "distance",
    "median",
    "min_max",
    "normalize",
    "percentage",
    "round_to",
    "safe_division",
    "standard_deviation",
    "variance",
]
