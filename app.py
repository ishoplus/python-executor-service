from flask import Flask, request, jsonify
import subprocess
import os
import tempfile
import uuid # Used for unique temporary file names

app = Flask(__name__)

@app.route('/execute-python', methods=['POST'])
def execute_python_code():
    data = request.get_json()
    python_code = data.get('code')

    if not python_code:
        return jsonify({"error": "No Python code provided"}), 400

    # Create a unique temporary file to store the Python code
    # This helps with isolation between different requests
    temp_dir = tempfile.gettempdir()
    unique_filename = f"script_{uuid.uuid4().hex}.py"
    script_path = os.path.join(temp_dir, unique_filename)

    try:
        # Write the Python code to the temporary file
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(python_code)

        # Execute the Python script using subprocess
        # Using python3 ensures the correct interpreter if both python and python3 exist
        process = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True, # Capture output as text (UTF-8)
            timeout=30 # Set a timeout for script execution (e.g., 30 seconds)
        )

        stdout = process.stdout
        stderr = process.stderr
        exit_code = process.returncode

        # Clean up the temporary file
        os.remove(script_path)

        return jsonify({
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code
        })

    except subprocess.TimeoutExpired:
        # If the script times out, ensure the process is killed
        process.kill()
        os.remove(script_path)
        return jsonify({"error": "Python script execution timed out"}), 408
    except Exception as e:
        # General error handling
        if os.path.exists(script_path):
            os.remove(script_path) # Clean up even on general error
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # Listen on all interfaces (0.0.0.0) and port 8000
    # Railway will expose this port
    app.run(host='0.0.0.0', port=8000)
