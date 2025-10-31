#!/usr/bin/env Rscript

# This code is for creating
# -----------------------------------------------------------------------------
# Date                     Programmer
#----------   --------------------------------------------------------------
# Oct-29-2025    Md Yousuf Ali (MdYousuf.Ali@fda.hhs.gov)
library(nanonext)
library(jsonlite)

# Create request socket (client)
client <- socket("req", dial = "tcp://127.0.0.1:5555")

# Send some data
test_data <- rnorm(100, mean = 50, sd = 15)
send(client, test_data, mode = "raw")
response <- recv(client, mode = "character")
stats <- fromJSON(response)
print(stats)

# Send shutdown signal to close Python server
send(client, -999, mode = "raw")  # Special shutdown signal

close(client)

# Example 1: Basic Data Exchange
## # Create request socket (client)
## client <- socket("req", dial = "tcp://127.0.0.1:5555")

## # Generate some test data
## test_data <- rnorm(1000, mean = 50, sd = 15)

## # Send data to Python (as raw bytes)
## send(client, test_data, mode = "raw")

## # Receive JSON response
## response <- recv(client, mode = "character")
## stats <- fromJSON(response)

## print(stats)
## close(client)


# 1_1 calculate from R after recieve data from python
library(nanonext)
library(jsonlite)

# Create a reply socket (server)
server <- socket("rep", listen = "tcp://127.0.0.1:5555")
cat("R server listening on tcp://127.0.0.1:5555\n")
cat("Waiting for data from Python...\n")

while (TRUE) {
  tryCatch({
    # Receive raw data from Python
    raw_data <- recv(server, mode = "raw", block = TRUE)

    if (!is_error_value(raw_data)) {
      # Convert raw bytes to numeric vector
      # Python sends float64, which is 8 bytes per number
      data <- readBin(raw_data, "double", n = length(raw_data) / 8)

      cat(sprintf("Received %d data points from Python\n", length(data)))
      cat(sprintf("Sample data: %.3f, %.3f, %.3f...\n", data[1], data[2], data[3]))

      # Process data in R
      r_mean <- mean(data)
      r_sd <- sd(data)
      r_median <- median(data)
      r_summary <- summary(data)

      # Create response with R analysis
      response <- list(
        r_mean = r_mean,
        r_sd = r_sd,
        r_median = r_median,
        r_summary = as.character(r_summary),
        length = length(data),
        message = "Data processed successfully by R"
      )

      # Send JSON response back to Python
      json_response <- toJSON(response, auto_unbox = TRUE)
      send(server, json_response, mode = "raw")

      cat("Response sent back to Python\n")
      cat(sprintf("R Analysis: mean=%.3f, sd=%.3f, median=%.3f\n",
                  r_mean, r_sd, r_median))

    } else {
      cat("Error receiving data\n")
    }

  }, error = function(e) {
    cat(sprintf("Error: %s\n", e$message))
    break
  }, interrupt = function(e) {
    cat("Interrupted by user\n")
    break
  })
}

close(server)
cat("R server closed\n")


# Example 2: Real-time Data Streaming
# Create subscriber socket
sub <- socket("sub", dial = "tcp://127.0.0.1:5556")

# Subscribe to sensor data topic
subscribe(sub, "sensor_data")

# Collect data for analysis
sensor_data <- list()
start_time <- Sys.time()

cat("Collecting sensor data from Python...\n")

# Collect data for 30 seconds
while (difftime(Sys.time(), start_time, units = "secs") < 30) {
  # Receive data (non-blocking)
  raw_msg <- recv(sub, mode = "character", block = FALSE)

  if (!is_error_value(raw_msg)) {
    # Parse the message (skip topic part)
    json_part <- strsplit(raw_msg, "\0", fixed = TRUE)[[1]][2]
    data <- fromJSON(json_part)

    sensor_data[[length(sensor_data) + 1]] <- data
    cat(sprintf("Received: Sensor %d, Temp: %.1f°C, Humidity: %.1f%%\n",
                data$sensor_id, data$temperature, data$humidity))
  }

  Sys.sleep(0.1)  # Small delay to prevent busy waiting
}

# Analyze collected data
if (length(sensor_data) > 0) {
  temps <- sapply(sensor_data, function(x) x$temperature)
  humidity <- sapply(sensor_data, function(x) x$humidity)

  cat(sprintf("\nAnalysis of %d readings:\n", length(sensor_data)))
  cat(sprintf("Temperature: Mean=%.1f°C, Range=%.1f-%.1f°C\n",
              mean(temps), min(temps), max(temps)))
  cat(sprintf("Humidity: Mean=%.1f%%, Range=%.1f-%.1f%%\n",
              mean(humidity), min(humidity), max(humidity)))
}

close(sub)

# Example 3: Bidirectional Data Processing Pipeline
# Create pair socket for bidirectional communication
socket <- socket("pair", dial = "ipc:///tmp/r_python_pipeline")

# Generate different types of data
datasets <- list(
  normal = rnorm(100, mean = 100, sd = 20),
  exponential = rexp(50, rate = 0.1),
  uniform = runif(75, min = 0, max = 50),
  bimodal = c(rnorm(50, 20, 5), rnorm(50, 80, 5))
)

# Process each dataset with Python
results <- list()
for (name in names(datasets)) {
  cat(sprintf("Processing %s dataset (%d points)...\n",
              name, length(datasets[[name]])))

  tryCatch({
    # Send data to Python
    send(socket, datasets[[name]], mode = "raw")

    # Receive processed result
    response <- recv(socket, mode = "character", block = 5000)

    if (!is_error_value(response)) {
      result <- fromJSON(response)
      results[[name]] <- result
      cat("✓ Successfully processed\n")
    }
  }, error = function(e) {
    cat(sprintf("✗ Error: %s\n", e$message))
  })

  Sys.sleep(0.5)  # Brief pause between requests
}

close(socket)

# Example 4: Asynchronous Machine Learning Pipeline
# Create async client
client <- socket("req", dial = "tcp://127.0.0.1:5557")

# Generate training data (iris-like dataset)
set.seed(123)
n_samples <- 1000
features <- matrix(rnorm(n_samples * 4), ncol = 4)
labels <- sample(0:2, n_samples, replace = TRUE)

cat("Starting model training...\n")

# Train model asynchronously
request <- list(
  action = "train",
  features = features,
  labels = labels
)

# Send training request asynchronously
send(client, toJSON(request), mode = "raw")

# Return async receive object
training_aio <- recv_aio(client, mode = "character", timeout = 30000)  # 30 second timeout

# Do other work while training
cat("Training in progress, doing other work...\n")
other_data <- rnorm(100)
summary(other_data)

# Check if training is complete
while (unresolved(training_aio)) {
  cat("Still training...\n")
  Sys.sleep(1)
}

# Get training results
training_result <- fromJSON(call_aio(training_aio)$data)
cat(sprintf("Training complete! Accuracy: %.3f\n", training_result$accuracy))

# Make predictions on new data
new_features <- matrix(rnorm(20 * 4), ncol = 4)
request <- list(
  action = "predict",
  features = new_features
)

send(client, toJSON(request), mode = "raw")
prediction_aio <- recv_aio(client, mode = "character", timeout = 5000)

# Get predictions
pred_result <- fromJSON(call_aio(prediction_aio)$data)
cat(sprintf("Predictions: %s\n", paste(pred_result$predictions, collapse = ", ")))

close(client)

# Example 5: Real-time Data Visualization Pipeline
# Create subscriber
sub <- socket("sub", dial = "tcp://127.0.0.1:5558")

# Subscribe to all sensor topics
subscribe(sub, "temp")
subscribe(sub, "press")
subscribe(sub, "vib")

# Data storage
temp_data <- numeric(0)
pressure_data <- numeric(0)
vibration_data <- numeric(0)
timestamps <- numeric(0)

cat("Collecting real-time data from Python sensors...\n")
start_time <- Sys.time()

# Collect data for 60 seconds
while (difftime(Sys.time(), start_time, units = "secs") < 60) {

  # Non-blocking receive
  msg <- recv(sub, mode = "character", block = FALSE)

  if (!is_error_value(msg)) {
    # Parse topic and data
    parts <- strsplit(msg, "\0", fixed = TRUE)[[1]]
    topic <- parts[1]
    data <- fromJSON(parts[2])

    # Store data by type
    timestamps <- c(timestamps, data$timestamp)

    switch(topic,
      "temp" = {
        temp_data <- c(temp_data, data$value)
        if (length(temp_data) %% 50 == 0) {
          cat(sprintf("Temperature: Current=%.1f°C, Avg=%.1f°C (n=%d)\n",
                      data$value, mean(tail(temp_data, 50)), length(temp_data)))
        }
      },
      "press" = {
        pressure_data <- c(pressure_data, data$value)
        if (length(pressure_data) %% 50 == 0) {
          cat(sprintf("Pressure: Current=%.1f hPa, Avg=%.1f hPa (n=%d)\n",
                      data$value, mean(tail(pressure_data, 50)), length(pressure_data)))
        }
      },
      "vib" = {
        vibration_data <- c(vibration_data, data$value)
        # Alert on high vibration
        if (data$value > 0.5) {
          cat(sprintf("⚠️  HIGH VIBRATION ALERT: %.3f\n", data$value))
        }
      }
    )
  }

  Sys.sleep(0.01)  # Small delay
}

# Final analysis
cat("\n=== FINAL ANALYSIS ===\n")
cat(sprintf("Temperature: %.1f°C ± %.1f (n=%d)\n",
            mean(temp_data), sd(temp_data), length(temp_data)))
cat(sprintf("Pressure: %.1f hPa ± %.1f (n=%d)\n",
            mean(pressure_data), sd(pressure_data), length(pressure_data)))
cat(sprintf("Vibration: %.3f ± %.3f (n=%d)\n",
            mean(vibration_data), sd(vibration_data), length(vibration_data)))

# Detect anomalies
high_vib_count <- sum(vibration_data > 0.3)
cat(sprintf("High vibration events: %d (%.1f%%)\n",
            high_vib_count, 100 * high_vib_count / length(vibration_data)))

close(sub)

# Example 6: Async File Processing
# Create async client
client <- socket("req", dial = "ipc:///tmp/file_processor")

# Create sample data file
sample_data <- data.frame(
  id = 1:1000,
  value = rnorm(1000, 50, 15),
  category = sample(c("A", "B", "C"), 1000, replace = TRUE),
  timestamp = seq.POSIXt(Sys.time() - 3600, Sys.time(), length.out = 1000)
)

csv_file <- tempfile(fileext = ".csv")
write.csv(sample_data, csv_file, row.names = FALSE)

cat("Starting async file processing...\n")

# Process file asynchronously
request <- list(action = "process_csv", filepath = csv_file)

# Send request
send(client, toJSON(request), mode = "raw")

# Return async receive
analysis_aio <- recv_aio(client, mode = "character", timeout = 10000)

# Do other work while Python processes the file
cat("File processing in background, doing other analysis...\n")
local_summary <- summary(sample_data$value)
print(local_summary)

# Check if Python analysis is complete
cat("Waiting for Python analysis...\n")
python_result <- fromJSON(call_aio(analysis_aio)$data)

if (python_result$status == "success") {
  cat("✓ Python analysis complete!\n")
  cat(sprintf("Dataset shape: %d rows × %d columns\n",
              python_result$shape[1], python_result$shape[2]))
  cat(sprintf("Columns: %s\n", paste(python_result$columns, collapse = ", ")))
  cat(sprintf("Missing values: %s\n",
              paste(names(python_result$missing_values)[python_result$missing_values > 0],
                    collapse = ", ")))
} else {
  cat("✗ Python analysis failed:", python_result$message, "\n")
}

# Clean up
unlink(csv_file)
close(client)

library(MCPR)
# MCPR handles sockets internally
mcpr_session_start()  # Creates nanonext sockets behind the scenes
execute_r_code("summary(mtcars)")  # Routes through nanonext automatically
