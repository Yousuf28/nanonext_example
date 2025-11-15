# R-Python Cross-Language Communication App

A GUI application demonstrating real-time data exchange between R and Python using [nanonext](https://github.com/r-lib/nanonext) sockets. This app provides a visual interface to send data between R and Python environments, showcasing seamless cross-language communication for data science workflows.

<!-- ![App Demo](demo-screenshot.png) -->

## Features

- **Real-time Communication**: Bidirectional data exchange between R and Python
- **Visual Interface**: Dual-panel GUI showing both R and Python environments
- **Data Statistics**: Send numeric data from Python and receive statistical analysis from R
- **Command Execution**: Execute R commands remotely from the Python interface
- **Connection Management**: Robust connection handling with retry logic and status monitoring
- **Detailed Logging**: Comprehensive logging of data transmission and processing

## What It Does

### Data Flow
```
Python GUI → Generate/Input Data → nanonext Socket → R Server → Statistical Analysis → JSON Response → Python Display
```

### Core Functionality
1. **Python Side**: Generates random data, accepts user input, sends data via nanonext sockets
2. **R Side**: Receives binary data, converts to R objects, performs statistical calculations, returns JSON results
3. **Communication**: Uses nanonext's high-performance messaging library for reliable data transfer
4. **Visualization**: Real-time display of data exchange, results, and system status

## Prerequisites

### R Requirements
```r
install.packages("nanonext")
install.packages("jsonlite")
```

### Python Requirements
```bash
pip install pynng numpy tkinter
```

## Installation & Setup

### 1. Install Dependencies

**R packages (open R console):**
```r
install.packages(c("nanonext", "jsonlite"))
```

**Python packages:**
```bash
pip install pynng numpy tkinter
```


## How to Run

### Step 1: Start R Server (Terminal 1)

Open R console and run:

```r
#R_server_run_this_first.R  or copy code below
library(nanonext)
library(jsonlite)

# Create server socket
server <- socket("rep", listen = "tcp://127.0.0.1:5556")
cat("R server listening on port 5556\n")

while(TRUE) {
  tryCatch({
    # Receive data
    raw_data <- recv(server, mode = "raw", block = TRUE)
    cat("Received", length(raw_data), "bytes\n")

    # Check for shutdown signal
    if(length(raw_data) == 1 && raw_data[1] == 255) {
      cat("Shutdown signal received\n")
      break
    }

    # Process numeric data (8-byte doubles)
    if(length(raw_data) %% 8 == 0 && length(raw_data) >= 8) {
      data <- readBin(raw_data, "double", n = length(raw_data)/8)
      cat("Converted to numeric:", paste(head(data, 10), collapse = ", "))
      if(length(data) > 10) cat(" ... (", length(data), "total values)")
      cat("\n")

      result <- list(
        mean = round(mean(data, na.rm = TRUE), 3),
        sd = round(sd(data, na.rm = TRUE), 3),
        min = round(min(data, na.rm = TRUE), 3),
        max = round(max(data, na.rm = TRUE), 3),
        length = length(data)
      )

      # Create clean JSON response
      json_response <- toJSON(result, auto_unbox = TRUE, pretty = FALSE)
      cat("Sending JSON response:", json_response, "\n")

      # Send as raw bytes
      send(server, json_response, mode = "raw")
      cat("Response sent successfully\n")

    } else {
      # Handle text commands
      command <- rawToChar(raw_data)
      cat("Executing R command:", command, "\n")

      result <- tryCatch({
        # Capture both output and result
        output <- capture.output({
          eval_result <- eval(parse(text = command))
          if(!is.null(eval_result)) print(eval_result)
        })
        if(length(output) > 0) {
          paste(output, collapse = "\n")
        } else {
          "Command executed (no output)"
        }
      }, error = function(e) {
        paste("Error:", e$message)
      })

      cat("Sending text response:", substr(result, 1, 100), "...\n")
      send(server, result, mode = "raw")
    }

  }, error = function(e) {
    cat("Server error:", e$message, "\n")
    error_msg <- paste("Server error:", e$message)
    send(server, error_msg, mode = "raw")
  })
}
# run until this

close(server)
```

**⚠️ Important**: When running the R server code, **do NOT run the `close(server)` line at the beginning**. This line only executes when you want to stop the server (when you send the shutdown signal or interrupt the loop).

### Step 2: Start Python GUI (Terminal 2)

```bash
python python_gui_app.py
```

### Step 3: Connect and Test

1. **Click "Connect to R"** - Wait for green "Connected" status
2. **Click "Test (1,2,3,4,5)"** - Verify basic communication works
3. **Click "Random Data"** - Send randomly generated dataset
4. **Try custom input** - Enter comma-separated numbers like: `10.5, 20.3, 30.7`
5. **Execute R commands** - Type R code like: `summary(1:100)` or `plot(1:10)`

## Usage Examples

### Data Exchange Examples
- **Simple test**: `1, 2, 3, 4, 5`
- **Random sample**: Click "Random Data" button
- **Custom dataset**: `15.2, 23.7, 31.1, 42.8, 55.3`
- **Large dataset**: Click "Large Dataset" button

### R Command Examples
- `x <- c(1, 2, 3, 4, 5)`
- `summary(mtcars)`
- `mean(rnorm(100))`
- `ls()` (list objects)
- `plot(1:10)` (creates plot)

## Expected Output

### Python Console Log:
```
[14:23:45] ✓ Connected to R server!
[14:23:47] → Sending random normal data (μ=50, σ=15): [52.34, 48.91, 55.67, ... 25 total values]
[14:23:47] ℹ Data size: 25 values, 200 bytes
[14:23:47] ← Raw response from R: '{"mean":49.876,"sd":14.523,"min":21.45,"max":78.32,"length":25,"sum":1246.9}'
[14:23:47] ✓ R computed statistics:
[14:23:47] ℹ   mean: 49.876
[14:23:47] ℹ   sd: 14.523
[14:23:47] ℹ   length: 25
```

### R Console Log:
```
R server listening on port 5556
--- REQUEST 1 ---
Received: 200 bytes
Data type: NUMERIC ARRAY
Values received: 25 numbers
First 10: 52.34, 48.91, 55.67, 43.21, 61.45, 38.92, 57.83, 44.76, 52.18, 49.33...
Computed statistics:
   mean: 49.876
   sd: 14.523
   min: 21.45
   max: 78.32
   length: 25
Sending JSON: {"mean":49.876,"sd":14.523,"min":21.45,"max":78.32,"length":25,"sum":1246.9}
Response sent successfully
```

## Troubleshooting

### Connection Issues
- **"Connection refused"**: Make sure R server is running first
- **"Already connected"**: Restart the Python app if connection gets stuck

### Data Issues  
- **"Invalid number format"**: Use comma-separated numbers like `1.5, 2.3, 3.7`
- **"JSON parsing failed"**: Restart both R server and Python app

### Performance Issues
- **Slow response**: Large datasets (>1000 values) may take longer to process
- **Memory usage**: Monitor R memory usage with very large datasets

## Technical Details

### Communication Protocol
- **Transport**: TCP sockets via nanonext (R) and pynng (Python)
- **Data Format**: Binary encoding for numeric arrays, UTF-8 for text
- **Response Format**: JSON for structured data, plain text for R command output

### Architecture
- **R Server**: Blocking receive loop, processes requests sequentially
- **Python Client**: Asynchronous GUI with threaded communication
- **Data Types**: Supports numeric arrays, text commands, and mixed data types

## Stopping the Application

1. **Python App**: Close the GUI window or Ctrl+C in terminal
2. **R Server**: The app sends a shutdown signal automatically, or press Ctrl+C in R console

## Use Cases

- **Data Science Workflows**: Send datasets from Python for R statistical analysis
- **Cross-Language Prototyping**: Test algorithms in both languages simultaneously  
- **Educational Demonstrations**: Show real-time data exchange between programming languages
- **Research Applications**: Combine Python's ML libraries with R's statistical capabilities

---

**Built with**: nanonext (R), pynng (Python), tkinter (GUI)  
**Inspired by**: [MCPR](https://github.com/phisanti/MCPR) framework for cross-language communication
