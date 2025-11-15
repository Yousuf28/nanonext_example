#!/usr/bin/env Rscript

# This code is for creating
# -----------------------------------------------------------------------------
# Date                     Programmer
#----------   --------------------------------------------------------------
# Oct-31-2025    Md Yousuf Ali (MdYousuf.Ali@fda.hhs.gov)

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

close(server)
cat("R server stopped\n")
