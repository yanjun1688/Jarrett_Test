"""
共享工具模块
提供跨应用使用的通用工具函数
"""

from .http_utils import (
    make_http_request,
    validate_url,
    parse_headers,
    build_query_string
)

from .date_utils import (
    format_datetime,
    parse_datetime,
    get_time_ago,
    convert_timezone,
    get_date_range
)

from .string_utils import (
    truncate_string,
    safe_json_parse,
    safe_json_stringify,
    generate_hash,
    sanitize_filename,
    extract_emails,
    extract_urls,
    camel_to_snake,
    snake_to_camel
)

from .validation import (
    validate_json_schema,
    validate_required_fields
)

from .logging_utils import (
    setup_logging,
    get_logger,
    log_execution_time
)

from .async_utils import (
    run_async,
    batch_process,
    with_timeout
)

from .command_utils import (
    get_npx_command,
    check_command_available
)

__all__ = [
    # HTTP工具
    'make_http_request',
    'validate_url',
    'parse_headers',
    'build_query_string',

    # 日期时间工具
    'format_datetime',
    'parse_datetime',
    'get_time_ago',
    'convert_timezone',
    'get_date_range',

    # 字符串工具
    'truncate_string',
    'safe_json_parse',
    'safe_json_stringify',
    'generate_hash',
    'sanitize_filename',
    'extract_emails',
    'extract_urls',
    'camel_to_snake',
    'snake_to_camel',

    # 验证工具
    'validate_json_schema',
    'validate_required_fields',

    # 日志工具
    'setup_logging',
    'get_logger',
    'log_execution_time',

    # 异步工具
    'run_async',
    'batch_process',
    'with_timeout',

    # 命令工具
    'get_npx_command',
    'check_command_available'
]
