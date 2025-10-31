#!/usr/bin/env python

# This code is for creating
# -----------------------------------------------------------------------------
# Date                     Programmer
#----------   --------------------------------------------------------------
# Oct-29-2025    Md Yousuf Ali (MdYousuf.Ali@fda.hhs.gov)
import pynng
import numpy as np
import json
import time
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
import pickle
import os

# Example 1: Basic Data Exchange Server

socket = pynng.Rep0(listen="tcp://127.0.0.1:5555")
print("Python server listening on tcp://127.0.0.1:5555")

try:
    while True:
        # Receive request from R
        raw_data = socket.recv()

        # Convert to numpy array
        data = np.frombuffer(raw_data, dtype=np.float64)
        print(f"Received from R: {data}")

        # Check for shutdown signal
        if len(data) == 1 and data[0] == -999:
            print("Received shutdown signal from R")
            break

        # Process data (example: calculate statistics)
        result = {
            "mean": float(np.mean(data)),
            "std": float(np.std(data)),
            "min": float(np.min(data)),
            "max": float(np.max(data)),
            "length": len(data)
        }

        # Send JSON response back to R
        response = json.dumps(result).encode('utf-8')
        socket.send(response)

except Exception as e:
    print(f"Error: {e}")
finally:
    socket.close()
    print("Socket closed")

# socket = pynng.Rep0(listen="tcp://127.0.0.1:5555")
# print("Python server listening on tcp://127.0.0.1:5555")

# while True:
#     try:
#         # Receive request from R
#         raw_data = socket.recv()

#         # Convert to numpy array
#         data = np.frombuffer(raw_data, dtype=np.float64)
#         print(f"Received from R: {data}")

#         # Process data (example: calculate statistics)
#         result = {
#             "mean": float(np.mean(data)),
#             "std": float(np.std(data)),
#             "min": float(np.min(data)),
#             "max": float(np.max(data)),
#             "length": len(data)
#         }

#         # Send JSON response back to R
#         response = json.dumps(result).encode('utf-8')
#         socket.send(response)

#     except KeyboardInterrupt:
#         break

# socket.close()

# 1_1 send from data python to R
import pynng
import numpy as np
import json

# Create a request socket (client)
socket = pynng.Req0(dial="tcp://127.0.0.1:5555")
print("Python client connected to tcp://127.0.0.1:5555")

# Generate some test data in Python
test_data = np.random.normal(100, 15, 500)  # 500 random numbers
print(f"Generated {len(test_data)} data points in Python")
print(f"Sample data: {test_data[:5]}...")

# Send data to R as raw bytes
data_bytes = test_data.tobytes()
socket.send(data_bytes)
print("Data sent to R server")

# Receive response from R
response = socket.recv()
result = json.loads(response.decode('utf-8'))

print("Response from R:")
print(f"  R calculated mean: {result['r_mean']:.3f}")
print(f"  R calculated sd: {result['r_sd']:.3f}")
print(f"  R calculated median: {result['r_median']:.3f}")
print(f"  R calculated summary: {result['r_summary']}")
print(f"  Data length confirmed: {result['length']}")

socket.close()


# Example 2: Real-time Data Streaming Publisher
pub = pynng.Pub0(listen="tcp://127.0.0.1:5556")
print("Python publisher started on tcp://127.0.0.1:5556")

sensor_id = 0
while True:
    try:
        # Generate simulated sensor data
        timestamp = time.time()
        temperature = 20 + 10 * np.sin(timestamp / 100) + np.random.normal(0, 2)
        humidity = 60 + 20 * np.cos(timestamp / 150) + np.random.normal(0, 5)

        # Create data packet
        data = {
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "temperature": round(temperature, 2),
            "humidity": round(humidity, 2)
        }

        # Send with topic "sensor_data"
        topic = "sensor_data"
        message = topic.encode() + b'\0' + json.dumps(data).encode()
        pub.send(message)

        print(f"Sent: {data}")
        sensor_id += 1
        time.sleep(1)  # Send every second

    except KeyboardInterrupt:
        break

pub.close()

# Example 3: Bidirectional Data Processing Pipeline
socket = pynng.Pair0(listen="ipc:///tmp/r_python_pipeline")
print("Python data processor ready")

scaler = StandardScaler()

while True:
    try:
        # Receive data from R
        raw_data = socket.recv()

        # Deserialize numpy array
        data = np.frombuffer(raw_data, dtype=np.float64).reshape(-1, 1)
        print(f"Received {len(data)} data points from R")

        # Process with scikit-learn
        if len(data) > 1:
            # Fit scaler and transform data
            scaled_data = scaler.fit_transform(data)

            # Calculate additional metrics
            result = {
                'scaled_data': scaled_data.flatten().tolist(),
                'original_mean': float(np.mean(data)),
                'original_std': float(np.std(data)),
                'scaled_mean': float(np.mean(scaled_data)),
                'scaled_std': float(np.std(scaled_data)),
                'n_points': len(data)
            }

            # Send processed data back
            response = json.dumps(result).encode()
            socket.send(response)
            print("Sent processed data back to R")

    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}")
        # Send error signal
        socket.send(b"ERROR")

socket.close()

# Example 4: Asynchronous Machine Learning Pipeline
socket = pynng.Rep0(listen="tcp://127.0.0.1:5557")
print("ML Model Server ready on tcp://127.0.0.1:5557")

model = RandomForestClassifier(n_estimators=100, random_state=42)
is_trained = False

while True:
    try:
        # Receive request
        request = json.loads(socket.recv().decode())
        action = request.get("action")

        if action == "train":
            # Train model
            X = np.array(request["features"])
            y = np.array(request["labels"])

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)

            is_trained = True
            response = {
                "status": "success",
                "accuracy": float(accuracy),
                "n_features": X.shape[1],
                "n_samples": len(X)
            }

        elif action == "predict" and is_trained:
            # Make predictions
            X_new = np.array(request["features"])
            predictions = model.predict(X_new).tolist()
            probabilities = model.predict_proba(X_new).tolist()

            response = {
                "status": "success",
                "predictions": predictions,
                "probabilities": probabilities
            }

        else:
            response = {
                "status": "error",
                "message": "Model not trained or invalid action"
            }

        # Send response
        socket.send(json.dumps(response).encode())

    except KeyboardInterrupt:
        break
    except Exception as e:
        response = {"status": "error", "message": str(e)}
        socket.send(json.dumps(response).encode())

socket.close()

# Example 5: Real-time Data Visualization Pipeline
pub = pynng.Pub0(listen="tcp://127.0.0.1:5558")
print("Python data generator started")

streams = ["temperature", "pressure", "vibration"]

while True:
    try:
        for stream_type in streams:
            # Generate realistic sensor data
            timestamp = time.time()

            if stream_type == "temperature":
                # Temperature with daily cycle + noise
                value = 20 + 10 * np.sin(timestamp / 3600) + np.random.normal(0, 2)
                topic = "temp"
            elif stream_type == "pressure":
                # Pressure with some trend + noise
                value = 1013 + 5 * np.sin(timestamp / 7200) + np.random.normal(0, 3)
                topic = "press"
            else:  # vibration
                # Vibration with occasional spikes
                base = np.random.normal(0.1, 0.02)
                spike = np.random.exponential(0.5) if np.random.random() < 0.05 else 0
                value = base + spike
                topic = "vib"

            # Create message
            data = {
                "timestamp": timestamp,
                "value": round(float(value), 3),
                "sensor_type": stream_type
            }

            # Send with topic prefix
            message = topic.encode() + b'\0' + json.dumps(data).encode()
            pub.send(message)

        time.sleep(0.1)  # 10 Hz data rate

    except KeyboardInterrupt:
        break

pub.close()

# Example 6: Async File Processing
socket = pynng.Rep0(listen="ipc:///tmp/file_processor")
print("Python file processor ready")

while True:
    try:
        # Receive file processing request
        request = json.loads(socket.recv().decode())
        action = request["action"]

        if action == "process_csv":
            filepath = request["filepath"]

            if os.path.exists(filepath):
                # Read and process CSV
                df = pd.read_csv(filepath)

                # Basic analysis
                result = {
                    "status": "success",
                    "shape": df.shape,
                    "columns": df.columns.tolist(),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "summary": df.describe().to_dict(),
                    "missing_values": df.isnull().sum().to_dict()
                }
            else:
                result = {"status": "error", "message": "File not found"}

        elif action == "filter_data":
            # Apply filters and return processed data
            filepath = request["filepath"]
            filters = request.get("filters", {})

            df = pd.read_csv(filepath)

            # Apply filters
            for col, condition in filters.items():
                if col in df.columns:
                    if condition["op"] == "gt":
                        df = df[df[col] > condition["value"]]
                    elif condition["op"] == "lt":
                        df = df[df[col] < condition["value"]]

            # Return filtered data
            result = {
                "status": "success",
                "data": df.to_dict("records"),
                "filtered_rows": len(df)
            }

        # Send response
        socket.send(json.dumps(result).encode())

    except KeyboardInterrupt:
        break
    except Exception as e:
        error_response = {"status": "error", "message": str(e)}
        socket.send(json.dumps(error_response).encode())

socket.close()
