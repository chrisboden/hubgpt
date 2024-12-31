# How to Add Logging to Code

## Overview

Adding logging to our codebase is crucial for debugging, monitoring, and understanding the flow of execution. This guide explains how to implement consistent, informative logging across the application.

## Logging Guidelines

### 1. Basic Structure

Every module should include these logging elements:
- Import required logging utilities
- Console output using termcolor for immediate visibility 
- File logging for persistent records
- Request/response logging for LLM interactions
- Function entry/exit logging
- Error and exception logging

```python
import logging
from termcolor import colored
from utils.log_utils import log_llm_request, log_llm_response, setup_logging

# Get logger for module
logger = logging.getLogger(__name__)
```

### 2. Key Points to Log

Log the following events:
- Function entry/exit points
- Major state transitions 
- API calls and external service interactions
- Error conditions and exceptions
- Important data transformations
- File operations
- Configuration changes
- Performance metrics
- Security events
- User actions

### 3. Implementation Steps

1. **Function Entry/Exit**
```python
logger.info("Starting %s with args: %s", function_name, args)
print(colored(f"Starting {function_name}", "cyan"))

# At function exit
logger.info("%s completed successfully", function_name)
print(colored(f"Completed {function_name}", "green"))
```

2. **API/External Service Calls** 
```python
# For LLM calls
log_llm_request(api_params)
print(colored("Making LLM API call", "yellow"))

# For other APIs
logger.info("Calling external API %s with params: %s", api_name, params)
response = make_api_call()
logger.info("API response received: %s", response)
```

3. **Data Operations**
```python
logger.debug("Processing data batch: %s", data_id)
logger.info("Transformed %d records", record_count)
```

4. **File Operations**
```python
logger.info("Reading file: %s", filepath)
logger.debug("File contents: %s", contents)
logger.info("Successfully wrote %d bytes to %s", bytes_written, filepath)
```

5. **Error Handling**
```python
try:
    operation() 
except Exception as e:
    error_msg = f"Error in {operation_name}: {str(e)}"
    print(colored(error_msg, "red"))
    logger.error(error_msg)
    logger.exception(e)
    raise
```

### 4. Color Coding Convention

Use these colors consistently:
- cyan: Function entry points and initialization
- yellow: Progress updates and state transitions
- green: Successful completions
- red: Errors and warnings
- blue: Informational messages
- magenta: Security/permission related messages

### 5. Log Levels

Use appropriate log levels:
- DEBUG: Detailed debugging information
- INFO: General operational events
- WARNING: Unexpected but handled situations
- ERROR: Error conditions requiring attention
- CRITICAL: System-level failures

### 6. Best Practices

- Keep log messages clear and concise
- Include relevant context (function name, parameters, IDs)
- Use structured logging for machine parsing
- Avoid logging sensitive information
- Include timestamps and correlation IDs
- Use consistent formatting
- Log at appropriate verbosity levels
- Rotate log files to manage storage
- Add metrics for important operations

### 7. Example Implementation

```python
def process_file(filepath: str, options: dict) -> dict:
    """Example function showing comprehensive logging."""
    logger.info("Starting process_file: %s", filepath)
    print(colored(f"Processing file: {filepath}", "cyan"))
    
    try:
        # Log file stats
        file_size = os.path.getsize(filepath)
        logger.debug("File size: %d bytes", file_size)
        
        # Log operation parameters
        logger.info("Processing options: %s", options)
        
        # Track timing
        start_time = time.time()
        
        # Perform operation
        result = do_processing()
        
        # Log metrics
        duration = time.time() - start_time
        logger.info("Processing completed in %.2f seconds", duration)
        print(colored("File processing successful", "green"))
        
        return {
            "status": "success",
            "result": result,
            "duration": duration
        }
        
    except Exception as e:
        error_msg = f"Failed to process file {filepath}: {str(e)}"
        print(colored(error_msg, "red"))
        logger.error(error_msg)
        logger.exception(e)
        return {"status": "error", "message": error_msg}
```

Remember to configure log rotation and retention policies to manage log files effectively. Focus on logging events that provide value for debugging, monitoring and auditing the application's behavior.