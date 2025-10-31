
# this is an example how claude desktop work
# run
# server_r_for_tkinter_app.R until close(server)

import tkinter as tk
from tkinter import ttk, scrolledtext
import pynng
import numpy as np
import json
import time
import threading
import queue

class EnhancedApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("R-Python Communication (Enhanced)")
        self.root.geometry("1200x700")

        self.socket = None
        self.connected = False
        self.output_queue = queue.Queue()

        self.setup_ui()
        self.update_display()

    def setup_ui(self):
        # Status and controls
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.status_label = ttk.Label(status_frame, text="Status: Disconnected", foreground="red")
        self.status_label.pack(side=tk.LEFT)

        ttk.Button(status_frame, text="Connect to R", command=self.connect_to_r).pack(side=tk.LEFT, padx=10)
        ttk.Button(status_frame, text="Test (1,2,3,4,5)", command=self.test_simple).pack(side=tk.LEFT, padx=5)
        ttk.Button(status_frame, text="Random Data", command=self.send_random_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(status_frame, text="Large Dataset", command=self.send_large_data).pack(side=tk.LEFT, padx=5)

        # Console
        console_frame = ttk.LabelFrame(self.root, text="Communication Log", padding=10)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.console = scrolledtext.ScrolledText(
            console_frame, height=25, width=100,
            bg='#1e1e1e', fg='#d4d4d4', font=('Consolas', 9)
        )
        self.console.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Input sections
        input_frame = ttk.Frame(console_frame)
        input_frame.pack(fill=tk.X)

        # Data input
        data_frame = ttk.Frame(input_frame)
        data_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(data_frame, text="Numbers (comma-separated):").pack(side=tk.LEFT)
        self.data_input = ttk.Entry(data_frame, width=50)
        self.data_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.data_input.bind('<Return>', self.send_custom_data)
        ttk.Button(data_frame, text="Send", command=self.send_custom_data).pack(side=tk.RIGHT)

        # R command input
        cmd_frame = ttk.Frame(input_frame)
        cmd_frame.pack(fill=tk.X)
        ttk.Label(cmd_frame, text="R command:").pack(side=tk.LEFT)
        self.cmd_input = ttk.Entry(cmd_frame, width=50)
        self.cmd_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.cmd_input.bind('<Return>', self.send_r_command)
        ttk.Button(cmd_frame, text="Execute", command=self.send_r_command).pack(side=tk.RIGHT)

    def log_message(self, message, msg_type="info"):
        """Add message to output queue with type"""
        timestamp = time.strftime("%H:%M:%S")
        prefix = {
            "info": "ℹ",
            "success": "✓",
            "error": "❌",
            "send": "→",
            "receive": "←"
        }.get(msg_type, "•")

        self.output_queue.put(f"[{timestamp}] {prefix} {message}")

    def connect_to_r(self):
        """Connect to R server"""
        def try_connect():
            if self.connected:
                self.log_message("Already connected!", "info")
                return

            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    self.log_message(f"Connecting to R server... attempt {attempt + 1}/{max_attempts}", "info")

                    if self.socket:
                        try:
                            self.socket.close()
                        except:
                            pass

                    self.socket = pynng.Req0()
                    self.socket.dial("tcp://127.0.0.1:5556")

                    self.connected = True
                    self.log_message("Connected to R server!", "success")
                    self.root.after(0, lambda: self.status_label.config(text="Status: Connected", foreground="green"))
                    return

                except Exception as e:
                    self.log_message(f"Connection attempt {attempt + 1} failed: {str(e)}", "error")
                    if attempt < max_attempts - 1:
                        time.sleep(1)

            self.log_message("Connection failed after all attempts", "error")
            self.log_message("Make sure R server is running first!", "info")

        threading.Thread(target=try_connect, daemon=True).start()

    def send_data_to_r(self, data, description="data"):
        """Send numeric data to R with detailed logging"""
        if not self.connected:
            self.log_message("Not connected to R server", "error")
            return

        def send():
            try:
                # Convert to numpy array
                data_array = np.array(data).astype(np.float64)
                data_bytes = data_array.tobytes()

                # Log what we're sending
                if len(data) <= 10:
                    data_preview = f"[{', '.join(f'{x:.2f}' for x in data)}]"
                else:
                    data_preview = f"[{', '.join(f'{x:.2f}' for x in data[:5])}, ... {len(data)} total values]"

                self.log_message(f"Sending {description}: {data_preview}", "send")
                self.log_message(f"Data size: {len(data)} values, {len(data_bytes)} bytes", "info")

                # Send data
                self.socket.send(data_bytes)

                # Receive response
                response_bytes = self.socket.recv()
                response_text = response_bytes.decode('utf-8').strip()

                self.log_message(f"Raw response from R: '{response_text}'", "receive")

                # Parse JSON response
                try:
                    result = json.loads(response_text)
                    self.log_message("R computed statistics:", "success")
                    for key, value in result.items():
                        self.log_message(f"  {key}: {value}", "info")

                except json.JSONDecodeError as je:
                    self.log_message(f"JSON parsing failed: {je}", "error")
                    self.log_message(f"Response length: {len(response_text)} chars", "info")
                    if len(response_text) > 100:
                        self.log_message(f"First 100 chars: '{response_text[:100]}'", "info")
                    else:
                        self.log_message(f"Full response: '{response_text}'", "info")

            except Exception as e:
                self.log_message(f"Communication error: {e}", "error")
                self.connected = False
                self.root.after(0, lambda: self.status_label.config(text="Status: Disconnected", foreground="red"))

        threading.Thread(target=send, daemon=True).start()

    def test_simple(self):
        """Test with simple data"""
        test_data = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.send_data_to_r(test_data, "simple test")

    def send_random_data(self):
        """Send random data with preview"""
        # Generate random data
        data = np.random.normal(50, 15, 25).tolist()
        self.send_data_to_r(data, "random normal data (μ=50, σ=15)")

    def send_large_data(self):
        """Send larger dataset"""
        data = np.random.uniform(0, 100, 100).tolist()
        self.send_data_to_r(data, "large uniform data (0-100)")

    def send_custom_data(self, event=None):
        """Send custom data from input"""
        data_str = self.data_input.get().strip()
        if not data_str:
            return

        try:
            # Parse comma-separated numbers
            data = [float(x.strip()) for x in data_str.split(',')]
            self.send_data_to_r(data, "custom input")
            self.data_input.delete(0, tk.END)
        except ValueError as e:
            self.log_message(f"Invalid number format: {e}", "error")
            self.log_message("Use format: 1.5, 2.3, 3.7, 4.1", "info")

    def send_r_command(self, event=None):
        """Send R command as text"""
        command = self.cmd_input.get().strip()
        if not command:
            return

        if not self.connected:
            self.log_message("Not connected to R server", "error")
            return

        def send():
            try:
                self.log_message(f"Executing R command: {command}", "send")

                # Send as text
                self.socket.send(command.encode('utf-8'))
                response = self.socket.recv()
                result = response.decode('utf-8').strip()

                self.log_message(f"R command result:", "receive")
                # Split long results into multiple lines
                if len(result) > 80:
                    lines = result.split('\n')
                    for line in lines:
                        self.log_message(f"  {line}", "info")
                else:
                    self.log_message(f"  {result}", "info")

                self.root.after(0, lambda: self.cmd_input.delete(0, tk.END))

            except Exception as e:
                self.log_message(f"Command execution error: {e}", "error")

        threading.Thread(target=send, daemon=True).start()

    def clear_console(self):
        """Clear console"""
        self.console.delete(1.0, tk.END)
        self.log_message("Console cleared", "info")

    def update_display(self):
        """Update console from queue"""
        try:
            while True:
                message = self.output_queue.get_nowait()
                self.console.insert(tk.END, f"{message}\n")
                self.console.see(tk.END)
        except queue.Empty:
            pass

        self.root.after(100, self.update_display)

    def run(self):
        try:
            self.log_message("App started - Click 'Connect to R' to begin", "info")
            self.root.mainloop()
        finally:
            if self.socket:
                try:
                    self.socket.send(bytes([255]))  # Shutdown signal
                    self.socket.close()
                except:
                    pass

if __name__ == "__main__":
    app = EnhancedApp()
    app.run()
